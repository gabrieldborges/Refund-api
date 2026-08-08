"""The three exception handlers, called directly.

Called directly rather than through fastapi's TestClient, which would add httpx
as a dependency — the same choice file_routes_test.py made. What matters here
is the mapping from exception to envelope; that the handlers are WIRED UP was
verified against the running API (four paths: business error, FastAPI
validation, unknown route, real 500).
"""
import json
import pytest
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from .server import (
    handle_http_exception,
    handle_unexpected_error,
    handle_validation_error,
)


class FakeUrl:
    path = "/refunds/1"


class FakeState:
    request_id = "req-test"


class FakeRequest:
    url = FakeUrl()
    state = FakeState()


def body_of(response) -> dict:
    return json.loads(response.body)


@pytest.mark.asyncio
async def test_a_business_error_becomes_a_problem_document():
    error = StarletteHTTPException(status_code=404, detail="Refund not found")

    response = await handle_http_exception(FakeRequest(), error)

    assert body_of(response)["detail"] == "Refund not found"
    assert body_of(response)["status"] == 404
    assert body_of(response)["instance"] == "/refunds/1"
    assert body_of(response)["request_id"] == "req-test"


# LIMITATION, stated because the obvious reading of this test is wrong: it
# proves the handler ACCEPTS Starlette's base exception, not that it is
# REGISTERED for it. Those are different, and only the second one was the bug.
#
# The real defect — @app.exception_handler(HTTPException) with FastAPI's
# subclass, which let the router's own 404 escape with the old {"detail": ...}
# shape — was found by asking the running API for a route that does not exist,
# and reintroducing it does NOT fail this file. Catching registration mistakes
# would need fastapi's TestClient, and therefore httpx as a dependency, which
# this project has declined twice now. See the pendency in current-state.md.
@pytest.mark.asyncio
async def test_the_handler_accepts_starlettes_own_exception():
    error = StarletteHTTPException(status_code=404, detail="Not Found")

    response = await handle_http_exception(FakeRequest(), error)

    assert response.media_type == "application/problem+json"


# THE SHAPE CHANGE THAT MATTERS. This used to reach the client as
# {"detail": [{...}]} and is why the frontend needed a function to tell two
# formats apart. Now detail is a sentence and the fields move to `errors`.
@pytest.mark.asyncio
async def test_a_validation_error_puts_fields_in_the_errors_extension():
    error = RequestValidationError(
        [{"loc": ("body", "password"), "msg": "Field required", "type": "missing"}]
    )

    response = await handle_validation_error(FakeRequest(), error)
    body = body_of(response)

    assert body["status"] == 422
    assert isinstance(body["detail"], str)
    assert body["errors"] == [{"field": "password", "message": "Field required"}]


@pytest.mark.asyncio
async def test_a_nested_field_keeps_its_path():
    error = RequestValidationError(
        [{"loc": ("body", "user", "email"), "msg": "Invalid email", "type": "value_error"}]
    )

    response = await handle_validation_error(FakeRequest(), error)

    assert body_of(response)["errors"][0]["field"] == "user.email"


# An unexpected failure must not leak what actually happened — a stack trace or
# a database message would go straight to the client.
@pytest.mark.asyncio
async def test_an_unexpected_error_does_not_leak_its_message():
    response = await handle_unexpected_error(FakeRequest(), RuntimeError("connection to db-prod-3 refused"))

    assert body_of(response)["detail"] == "Internal server error"
    assert "db-prod-3" not in response.body.decode()


# The request_id is the only thing that makes a 500 reportable: the user quotes
# it and it matches a log line (Item 24 will reuse this same id).
@pytest.mark.asyncio
async def test_an_unexpected_error_still_carries_the_request_id():
    response = await handle_unexpected_error(FakeRequest(), RuntimeError("boom"))

    assert body_of(response)["request_id"] == "req-test"
    assert response.headers["X-Request-Id"] == "req-test"
