"""The API over HTTP, end to end.

The 32 integration tests that came before this one all sat BELOW the HTTP
layer: repositories, migrations, lock contention, object storage. None of them
went through a route, so none exercised middleware, routing, the composer, the
view, or the exception handlers being wired to the right thing.

That gap has a track record. Three items in a row shipped a defect of exactly
this shape — a correct part that was not correctly joined:

  Item 23  the handler was right; its REGISTRATION was on the wrong class
  Item 24  the filter was right; it was never INSTALLED on the handler
  2026-08  the message was right; it was never REACHED

Each was found by running the app by hand. These tests are the automated
version of running it by hand.
"""
import pytest
from src.configs.settings import settings


@pytest.mark.integration
def test_health_answers_without_authentication(api_client):
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_registering_then_logging_in_returns_a_usable_token(api_client):
    api_client.post(
        "/auth/register",
        json={"name": "Ana", "email": "flow@example.com", "password": "Senha123!"},
    )

    login = api_client.post(
        "/auth/login", json={"email": "flow@example.com", "password": "Senha123!"}
    )
    token = login.json()["token"]

    # The token is only proven usable by using it.
    listing = api_client.get("/refunds", headers={"Authorization": f"Bearer {token}"})
    assert listing.status_code == 200


@pytest.mark.integration
def test_a_wrong_password_is_a_problem_document(api_client):
    api_client.post(
        "/auth/register",
        json={"name": "Ana", "email": "wrong@example.com", "password": "Senha123!"},
    )

    response = api_client.post(
        "/auth/login", json={"email": "wrong@example.com", "password": "errada"}
    )

    assert response.status_code == 400
    assert response.headers["content-type"] == "application/problem+json"
    assert isinstance(response.json()["detail"], str)


@pytest.mark.integration
def test_a_request_without_a_token_is_refused(api_client):
    response = api_client.get("/refunds")

    assert response.status_code == 401
    assert response.json()["status"] == 401


@pytest.mark.integration
def test_a_forged_token_is_refused(authenticated):
    client, _, _ = authenticated

    response = client.get("/refunds", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401


# --------------------------------------------------------------------------
# The error envelope, at the layer that actually serves it
# --------------------------------------------------------------------------


# THE PENDENCY THIS ITEM CLOSES. Registering the handler on FastAPI's
# HTTPException instead of Starlette's let the ROUTER's own 404 escape with the
# old {"detail": ...} shape, and reintroducing that failed no test — the unit
# tests call the handlers directly, which proves the mapping and not the
# registration. Only a request through the router can tell the difference.
@pytest.mark.integration
def test_an_unknown_route_is_also_a_problem_document(api_client):
    response = api_client.get("/rota-que-nao-existe")

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"] == "about:blank"
    assert response.json()["instance"] == "/rota-que-nao-existe"


@pytest.mark.integration
def test_every_error_carries_a_request_id_matching_the_header(api_client):
    response = api_client.get("/rota-que-nao-existe")

    assert response.json()["request_id"] == response.headers["x-request-id"]


# FastAPI's own validation used to arrive as a LIST under `detail`, the second
# shape that forced the frontend to branch. This is the layer where that
# conversion happens.
@pytest.mark.integration
def test_a_validation_error_carries_field_level_errors(api_client):
    response = api_client.post("/auth/login", json={"email": "a@b.com"})

    body = response.json()
    assert response.status_code == 422
    assert isinstance(body["detail"], str)
    assert body["errors"][0]["field"] == "password"


# --------------------------------------------------------------------------
# A refund, all the way through
# --------------------------------------------------------------------------


def create_refund(client, headers, name="Almoço", filename="recibo.png"):
    return client.post(
        "/refunds",
        headers=headers,
        data={"name": name, "category": "food", "amount": "15.00"},
        files={"file": (filename, b"bytes do comprovante", "image/png")},
    )


@pytest.mark.integration
def test_a_refund_can_be_created_listed_read_and_deleted(authenticated):
    client, headers, user_id = authenticated

    created = create_refund(client, headers)
    assert created.status_code == 201
    refund_id = created.json()["attributes"]["id"]

    listing = client.get("/refunds", headers=headers).json()
    assert listing["total"] == 1
    assert listing["attributes"][0]["id"] == refund_id

    detail = client.get(f"/refunds/{refund_id}", headers=headers).json()["attributes"]
    assert detail["name"] == "Almoço"
    assert detail["status"] == "pending"
    assert detail["user"]["id"] == user_id

    assert client.delete(f"/refunds/{refund_id}", headers=headers).status_code == 200
    assert client.get(f"/refunds/{refund_id}", headers=headers).status_code == 404


# The response must not leak the stored filename — the rule the serializer was
# extracted for. Asserted here because this is the only place the whole
# serialisation path runs.
@pytest.mark.integration
def test_the_stored_filename_never_reaches_the_client(authenticated):
    client, headers, _ = authenticated
    refund_id = create_refund(client, headers).json()["attributes"]["id"]

    detail = client.get(f"/refunds/{refund_id}", headers=headers).json()["attributes"]

    assert "filename" not in detail
    assert "avatar_filename" not in detail["user"]
    assert detail["user"]["has_avatar"] is False


# THE POINT OF ITEM 22, exercised over real HTTP: the API answers a signed URL,
# and that URL serves the bytes with NO Authorization header. The browser check
# proved this once by hand; this is the repeatable version.
@pytest.mark.integration
def test_the_receipt_url_serves_the_file_without_a_token_header(authenticated):
    client, headers, _ = authenticated
    refund_id = create_refund(client, headers).json()["attributes"]["id"]

    metadata = client.get(f"/refunds/{refund_id}/receipt", headers=headers).json()
    assert metadata["media_type"] == "image/png"

    # Deliberately WITHOUT headers — an <img> tag cannot send them.
    path = metadata["url"].split("localhost:3333")[-1]
    file_response = client.get(path)

    assert file_response.status_code == 200
    assert file_response.content == b"bytes do comprovante"


@pytest.mark.integration
def test_a_tampered_signature_is_refused(authenticated):
    client, headers, _ = authenticated
    refund_id = create_refund(client, headers).json()["attributes"]["id"]

    url = client.get(f"/refunds/{refund_id}/receipt", headers=headers).json()["url"]
    path = url.split("localhost:3333")[-1]
    tampered = path[:-3] + ("aaa" if not path.endswith("aaa") else "bbb")

    assert client.get(tampered).status_code == 404


# Anti-enumeration (BR-013): another user's refund answers exactly like one
# that does not exist. Only a real request can show that both produce the same
# status AND the same body.
@pytest.mark.integration
def test_someone_elses_refund_is_indistinguishable_from_a_missing_one(authenticated):
    client, headers, _ = authenticated
    mine = create_refund(client, headers).json()["attributes"]["id"]

    client.post(
        "/auth/register",
        json={"name": "Outro", "email": "outro@example.com", "password": "Senha123!"},
    )
    other_token = client.post(
        "/auth/login", json={"email": "outro@example.com", "password": "Senha123!"}
    ).json()["token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    not_yours = client.get(f"/refunds/{mine}", headers=other_headers)
    missing = client.get("/refunds/999999", headers=other_headers)

    assert not_yours.status_code == missing.status_code == 404
    assert not_yours.json()["detail"] == missing.json()["detail"]


# A standard user must not be able to review, and the check must happen before
# any database lookup (the ordering decision recorded in UC-007).
@pytest.mark.integration
def test_a_standard_user_cannot_review_a_refund(authenticated):
    client, headers, _ = authenticated
    refund_id = create_refund(client, headers).json()["attributes"]["id"]

    response = client.patch(
        f"/refunds/{refund_id}/status", headers=headers, json={"status": "approved"}
    )

    assert response.status_code == 403


# --------------------------------------------------------------------------
# Admin flows — added by Item 26, which found them at 0% over HTTP
# --------------------------------------------------------------------------
#
# The coverage report put refund_routes at 77% and user_routes at 59%, with the
# payment routes, the review route and every avatar route never once reached by
# a request. Those are the authorization-heavy paths: exactly what the item's
# practice line ("usar o relatório para encontrar autorização/falha parcial
# esquecida") asks for.


@pytest.mark.integration
def test_an_admin_can_approve_and_then_pay_a_refund(authenticated, admin_headers):
    client, headers, _ = authenticated
    refund_id = create_refund(client, headers).json()["attributes"]["id"]

    approved = client.patch(
        f"/refunds/{refund_id}/status", headers=admin_headers, json={"status": "approved"}
    )
    assert approved.status_code == 200

    paid = client.post(
        f"/refunds/{refund_id}/payment",
        headers=admin_headers,
        files={"file": ("comprovante.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert paid.status_code == 200
    assert paid.json()["attributes"]["status"] == "paid"


# BR-016: an admin must not decide on their own request. Enforced before any
# database lookup, and never exercised through a real request until now.
@pytest.mark.integration
def test_an_admin_cannot_review_their_own_refund(api_client, admin_headers):
    own = create_refund(api_client, admin_headers).json()["attributes"]["id"]

    response = api_client.patch(
        f"/refunds/{own}/status", headers=admin_headers, json={"status": "approved"}
    )

    assert response.status_code == 403


@pytest.mark.integration
def test_the_payment_receipt_is_served_to_the_owner(authenticated, admin_headers):
    client, headers, _ = authenticated
    refund_id = create_refund(client, headers).json()["attributes"]["id"]
    client.patch(
        f"/refunds/{refund_id}/status", headers=admin_headers, json={"status": "approved"}
    )
    client.post(
        f"/refunds/{refund_id}/payment",
        headers=admin_headers,
        files={"file": ("comprovante.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )

    # The OWNER, not the admin — the payment receipt is readable by both, and
    # the owner is the case a standard user actually hits.
    metadata = client.get(f"/refunds/{refund_id}/payment-receipt", headers=headers).json()
    assert metadata["media_type"] == "application/pdf"

    path = metadata["url"].split("localhost:3333")[-1]
    assert client.get(path).content == b"%PDF-1.4 fake"


# An unpaid refund answers exactly like an unknown one — one of the four
# identical 404 paths verified byte for byte when the endpoint was built, and
# never checked over HTTP since.
@pytest.mark.integration
def test_an_unpaid_refund_has_no_payment_receipt(authenticated):
    client, headers, _ = authenticated
    refund_id = create_refund(client, headers).json()["attributes"]["id"]

    unpaid = client.get(f"/refunds/{refund_id}/payment-receipt", headers=headers)
    unknown = client.get("/refunds/999999/payment-receipt", headers=headers)

    assert unpaid.status_code == unknown.status_code == 404
    assert unpaid.json()["detail"] == unknown.json()["detail"]


@pytest.mark.integration
def test_the_review_history_records_who_decided_and_when(authenticated, admin_headers):
    client, headers, _ = authenticated
    refund_id = create_refund(client, headers).json()["attributes"]["id"]
    client.patch(
        f"/refunds/{refund_id}/status",
        headers=admin_headers,
        json={"status": "rejected", "reason": "Duplicado"},
    )

    history = client.get(f"/refunds/{refund_id}/reviews", headers=headers).json()

    assert history["count"] == 1
    assert history["attributes"][0]["to_status"] == "rejected"
    assert history["attributes"][0]["reason"] == "Duplicado"


# --------------------------------------------------------------------------
# Avatar routes — user_routes.py was at 59%, all of it here
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_an_avatar_can_be_uploaded_read_and_removed(authenticated):
    client, headers, user_id = authenticated

    upload = client.post(
        "/users/me/avatar", headers=headers, files={"file": ("foto.png", b"png", "image/png")}
    )
    assert upload.status_code == 200

    # has_avatar is what the refund responses expose instead of the filename.
    refund_id = create_refund(client, headers).json()["attributes"]["id"]
    detail = client.get(f"/refunds/{refund_id}", headers=headers).json()["attributes"]
    assert detail["user"]["has_avatar"] is True

    metadata = client.get(f"/users/{user_id}/avatar", headers=headers).json()
    assert client.get(metadata["url"].split("localhost:3333")[-1]).content == b"png"

    assert client.delete("/users/me/avatar", headers=headers).status_code == 200
    assert client.get(f"/users/{user_id}/avatar", headers=headers).status_code == 404


# BR-021: any authenticated user may read any avatar — there is no
# authorization decision here, only a lookup, and that is worth pinning.
@pytest.mark.integration
def test_any_authenticated_user_can_read_another_users_avatar(authenticated, admin_headers):
    client, headers, user_id = authenticated
    client.post(
        "/users/me/avatar", headers=headers, files={"file": ("foto.png", b"png", "image/png")}
    )

    assert client.get(f"/users/{user_id}/avatar", headers=admin_headers).status_code == 200


# --------------------------------------------------------------------------
# Abuse controls (Item 27) — the threats modelled before writing them
# --------------------------------------------------------------------------


# Login answers the same message for "no such user" and "wrong password" on
# purpose, so an attacker cannot learn which emails exist. Nothing stopped them
# trying ten thousand times against one they already knew — and bcrypt makes
# every attempt expensive for the SERVER, so this was CPU exhaustion too.
@pytest.mark.integration
def test_repeated_login_attempts_are_eventually_refused(api_client):
    for _ in range(settings.login_rate_limit):
        api_client.post("/auth/login", json={"email": "a@b.com", "password": "errada"})

    blocked = api_client.post("/auth/login", json={"email": "a@b.com", "password": "errada"})

    assert blocked.status_code == 429
    assert blocked.headers["content-type"] == "application/problem+json"


# Registration answers "Email already registered", which is useful to a person
# and is exactly what login refuses to reveal. The decision was to keep the
# message and make BULK enumeration impractical.
@pytest.mark.integration
def test_bulk_registration_attempts_are_refused(api_client):
    for index in range(settings.register_rate_limit):
        api_client.post(
            "/auth/register",
            json={"name": "A", "email": f"probe{index}@example.com", "password": "Senha123!"},
        )

    blocked = api_client.post(
        "/auth/register",
        json={"name": "A", "email": "probe999@example.com", "password": "Senha123!"},
    )

    assert blocked.status_code == 429


# Burning the login allowance must not block a legitimate registration.
@pytest.mark.integration
def test_the_two_limits_are_independent(api_client):
    for _ in range(settings.login_rate_limit + 1):
        api_client.post("/auth/login", json={"email": "a@b.com", "password": "x"})

    registration = api_client.post(
        "/auth/register",
        json={"name": "A", "email": "livre@example.com", "password": "Senha123!"},
    )

    assert registration.status_code == 201


# THE UPLOAD THREAT. Every upload route does `content = await file.read()` and
# the validators check the 4MB limit AFTERWARDS — by which point the body is
# already in memory. This is refused on Content-Length, before the route reads
# a byte.
@pytest.mark.integration
def test_an_oversized_body_is_refused_before_it_is_buffered(authenticated):
    client, headers, _ = authenticated
    huge = b"x" * (settings.max_request_body_bytes + 1024)

    response = client.post(
        "/refunds",
        headers=headers,
        data={"name": "Grande", "category": "food", "amount": "10.00"},
        files={"file": ("grande.png", huge, "image/png")},
    )

    assert response.status_code == 413
    assert response.json()["status"] == 413


# A normal upload must still pass — a size guard that blocks real files would
# be a worse outage than the one it prevents.
@pytest.mark.integration
def test_a_normal_upload_is_unaffected(authenticated):
    client, headers, _ = authenticated

    assert create_refund(client, headers).status_code == 201


@pytest.mark.integration
def test_security_headers_are_present_on_every_response(api_client):
    response = api_client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    # Keeps a signed file URL, which carries a token in its query, out of the
    # Referer header when a browser navigates away.
    assert response.headers["Referrer-Policy"] == "no-referrer"


# REGRESSION. X-Frame-Options: DENY was applied to every response including
# /files, and a PDF preview renders through <object> — which IS framing. Images
# kept working because <img> is not framing, so the symptom read as "PDFs are
# broken" rather than "a header is too broad". Reported from the browser; no
# test caught it, because the Item 27 tests asserted the header was PRESENT,
# which it correctly was.
#
# The assertion is deliberately about the ABSENCE of the header on this path.
@pytest.mark.integration
def test_file_responses_can_be_embedded_by_the_frontend(authenticated):
    client, headers, _ = authenticated
    refund_id = create_refund(client, headers).json()["attributes"]["id"]
    url = client.get(f"/refunds/{refund_id}/receipt", headers=headers).json()["url"]

    response = client.get(url.split("localhost:3333")[-1])

    assert "X-Frame-Options" not in response.headers
    # Replaced by the modern header, which unlike X-Frame-Options can name WHO
    # may embed — SAMEORIGIN would not do, since the file comes from the API's
    # port and the page from the frontend's.
    policy = response.headers["Content-Security-Policy"]
    assert "frame-ancestors" in policy
    for origin in settings.cors_origins:
        assert origin in policy


# The relaxation must be confined to /files. An API response embedded anywhere
# is still clickjacking material.
@pytest.mark.integration
def test_api_responses_still_refuse_to_be_framed(api_client):
    response = api_client.get("/health")

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Content-Security-Policy"] == "frame-ancestors 'none'"


# READINESS is a different question from liveness: "can this instance serve?",
# not "is the process alive?". Until Item 30 nothing answered it — /health said
# ok with the database unreachable, measured — and an orchestrator reading that
# keeps routing users to an instance that cannot answer anything.
@pytest.mark.integration
def test_readiness_reports_ready_when_the_database_answers(api_client):
    response = api_client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.integration
def test_liveness_and_readiness_are_different_endpoints(api_client):
    assert api_client.get("/health").json() == {"status": "ok"}
    assert api_client.get("/ready").json() == {"status": "ready"}
