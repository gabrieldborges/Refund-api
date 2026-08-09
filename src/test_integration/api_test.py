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
