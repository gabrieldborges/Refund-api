"""Fixtures shared by the route tests in this directory.

The bootstrap below appeared verbatim in the summary and daily-counts route tests,
and pylint's R0801 caught it. Hoisting it here is the remedy AGENTS.md prescribes for
fixtures repeated across tests of the same directory.

What these tests are for: routing and wiring. The auth dependency is OVERRIDDEN
rather than a real token minted, because JWT decoding is auth_jwt's own test — here
the question is whether a path reaches the composer it should, and whether the query
arrives shaped as the view expects.
"""
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from src.main.server.server import app
from src.main.middlewares.auth_jwt import get_current_user
from src.views.http_types.http_response import HttpResponse

STANDARD_TOKEN = {"user_id": 1, "role": "standard"}
ADMIN_TOKEN = {"user_id": 1, "role": "admin"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def view():
    """Builds a fake view that answers 200 with the given body.

    A factory rather than a ready object: each test wants a different body, and a
    single shared instance would carry the previous test's call args.
    """

    def build(body):
        fake = AsyncMock()
        fake.handle.return_value = HttpResponse(body=body, status_code=200)
        return fake

    return build


@pytest.fixture
def as_standard():
    """Speaks as a standard user, and undoes the override afterwards.

    The teardown matters: dependency_overrides lives on the app object, which is
    shared across the whole session, so a test that forgot to clear it would leak
    into whatever runs next.
    """
    app.dependency_overrides[get_current_user] = lambda: STANDARD_TOKEN
    yield STANDARD_TOKEN
    app.dependency_overrides.clear()


@pytest.fixture
def as_admin():
    app.dependency_overrides[get_current_user] = lambda: ADMIN_TOKEN
    yield ADMIN_TOKEN
    app.dependency_overrides.clear()
