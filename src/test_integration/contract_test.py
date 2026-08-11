"""Captures the API's REAL responses into a versioned contract file.

WHY THIS EXISTS. The frontend validates every response with Zod schemas
written by hand, and its test suite runs against MSW handlers also written by
hand. Both are guesses at what this API returns, and both have been wrong:

  - refundStatusSchema knew three statuses while the API answered a fourth
    ("paid"). The first paid refund would have put every user's Home into
    isError.
  - user_id moved from the top level into a nested user object.
  - the list fixture answered page 1 to a request for page 2 — recorded as
    "desonesta" and still live.
  - the reviews fixture was not chronological while mocking a contract that
    says it is.

Each was found late: two in a browser, one in a review. A contract file turns
that class of divergence into a red test.

HOW IT WORKS, AND WHAT IT DOES NOT COVER. This test drives the real API and
writes the payloads to contract/. It then compares against what is committed
and FAILS if they differ, so a shape change that nobody regenerated cannot pass
CI here.

The frontend keeps its own copy and validates it with its own Zod schemas.
That copy is **synchronised by hand**, because the two repositories are
independent and each CI checks out only one of them. So this catches "the API
changed and the contract was not regenerated" and "the frontend's schemas do
not match the contract" — but NOT "the contract was regenerated and the
frontend's copy was never updated". That last gap is the price of two repos,
and it is the same shape as the stale-SHA problem this project has recorded
six times: it is written down precisely so nobody trusts the file further than
it deserves.

Values that change every run (ids, timestamps, tokens, filenames) are
normalised to fixed placeholders OF THE SAME TYPE, so the file is stable
without lying about its shape.
"""
import json
import pathlib
import pytest


# TWO files, not one, and the split is dictated by the frontend's own layering
# rule rather than by taste. eslint-plugin-boundaries (Item 9) classifies
# src/schemas and src/test as the `app` layer and forbids a feature importing
# from it, so a refunds test cannot read a file that also carries the login
# payload. Each half therefore lands where its schemas already live:
#
#   refunds.json -> Refund-FrontEnd/src/features/refunds/contract/
#   app.json     -> Refund-FrontEnd/src/test/contract/
#
#   users.json   -> Refund-FrontEnd/src/features/team/contract/
CONTRACT_PATHS = {
    "refunds": pathlib.Path("contract/refunds.json"),
    "app": pathlib.Path("contract/app.json"),
    "users": pathlib.Path("contract/users.json"),
}


def normalise(value):
    """Replace volatile values with fixed ones of the same type.

    Type-preserving on purpose: an id becomes another integer, not the string
    "<id>". The frontend validates this file with schemas that check types, so
    a placeholder of the wrong type would make the contract useless.
    """
    if isinstance(value, dict):
        return {key: normalise_field(key, item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalise(item) for item in value]
    return value


VOLATILE = {
    "id": 1,
    "user_id": 1,
    "reviewer_id": 1,
    "refund_id": 1,
    "token": "eyJhbGciOiJIUzI1NiJ9.CONTRACT.SIGNATURE",
    "created_at": "2026-01-01T12:00:00",
    "reviewed_at": "2026-01-01T12:00:00",
    "url": "http://localhost:3333/files/receipts/file.png?token=CONTRACT",
    "request_id": "00000000-0000-0000-0000-000000000000",
}


def normalise_field(key, value):
    if key in VOLATILE and not isinstance(value, (dict, list)):
        return VOLATILE[key]
    return normalise(value)


def create_refund(client, headers):
    return client.post(
        "/refunds",
        headers=headers,
        data={"name": "Almoço com cliente", "category": "food", "amount": "45.90"},
        files={"file": ("recibo.png", b"bytes", "image/png")},
    )


def capture_refunds(client, headers, user_id):
    created = create_refund(client, headers)
    refund_id = created.json()["attributes"]["id"]

    return {
        "refundCreate": created.json(),
        "refundList": client.get("/refunds", headers=headers).json(),
        "refundDetail": client.get(f"/refunds/{refund_id}", headers=headers).json(),
        "receiptUrl": client.get(f"/refunds/{refund_id}/receipt", headers=headers).json(),
        "refundReviews": client.get(f"/refunds/{refund_id}/reviews", headers=headers).json(),
        "refundStats": client.get(f"/users/{user_id}/refund-stats", headers=headers).json(),
    }


def capture_app(client):
    return {
        # Flat, with no {type, count, attributes} envelope — unlike every refund
        # response above. Three envelope styles coexist in this API; capturing
        # them is how the frontend finds out instead of guessing.
        "login": client.post(
            "/auth/login", json={"email": "api@example.com", "password": "Senha123!"}
        ).json(),
        # The error envelope is part of the contract too: getApiErrorMessage
        # reads `detail` out of it on seven screens.
        "problemDocument": client.get("/rota-inexistente").json(),
    }


def capture_users(client, admin_headers, user_id):
    """Captured with the ADMIN's headers, not the standard user's.

    Both routes are admin-only (BR-025), so a standard user's token would record
    a 403 body as if it were the contract. With both fixtures active there are
    two users — Ana from `authenticated` and Chefe from `admin_headers` — so the
    list snapshot has more than one row and a per-row shape error cannot hide in
    a single-element array.
    """
    return {
        "userList": client.get("/users", headers=admin_headers).json(),
        "userDetail": client.get(f"/users/{user_id}", headers=admin_headers).json(),
    }


@pytest.mark.integration
def test_the_contract_file_matches_what_the_api_actually_returns(authenticated, admin_headers):
    client, headers, user_id = authenticated

    captures = (
        ("refunds", capture_refunds(client, headers, user_id)),
        ("app", capture_app(client)),
        ("users", capture_users(client, admin_headers, user_id)),
    )

    stale = []
    for name, captured in captures:
        path = CONTRACT_PATHS[name]
        current = json.dumps(normalise(captured), ensure_ascii=False, indent=2, sort_keys=True)
        current += "\n"

        path.parent.mkdir(exist_ok=True)
        previous = path.read_text(encoding="utf-8") if path.exists() else None
        path.write_text(current, encoding="utf-8")

        if previous != current:
            stale.append(str(path))

    assert not stale, (
        f"The API's responses changed and {', '.join(stale)} was stale. It has been "
        "regenerated — review the diff, commit it, AND copy it to the frontend "
        "(refunds.json -> src/features/refunds/contract/, app.json -> "
        "src/test/contract/, users.json -> src/features/team/contract/), or the "
        "frontend keeps validating the old shape."
    )
