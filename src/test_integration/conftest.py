"""Fixtures for the tests that run against a real PostgreSQL.

Everything here is deliberately outside the mocked suite. A mock answers what
we told it to answer, so it proves the repository builds the SQL we intended —
never that PostgreSQL accepts it, applies the constraints, or behaves the way
we assume under a lock. Both bugs this project found the hard way (the shared
session in DatabaseConnectionHandler, and `paid` not being terminal) were
invisible to the mocked suite by construction.

Requires `docker compose up -d`. These tests are excluded by default (see
pytest.ini); run them with `pytest -m integration`.
"""
# pylint: disable=redefined-outer-name
# redefined-outer-name: expected with pytest fixtures — a fixture that consumes
# another declares a parameter with the same name as the fixture function. Same
# disable, for the same reason, as src/models/repositories/conftest.py.
#
# Import order note: `alembic` is a third-party package, but pylint classifies
# it as first-party here because this repository has an alembic/ directory at
# its root. The grouping below follows that classification rather than fighting
# it — stdlib, then third party, then what pylint considers local.
import os
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config
from src.configs.settings import settings
from src.drivers.storage_factory import LOCAL_DIRECTORIES
from src.main.middlewares.rate_limit import rate_limiter
from src.main.server.server import app
from src.models.settings.database_connection_handler import (
    DatabaseConnectionHandler,
    build_engine,
    get_engine,
    get_session_factory,
)


# Matches docker-compose.yml. Overridable so CI can point at its own service
# container without editing this file.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://refund_test:refund_test@localhost:5433/refund_test",
)


def alembic_config(url: str = TEST_DATABASE_URL) -> Config:
    """An Alembic config aimed at the throwaway database.

    alembic/env.py only falls back to settings.database_url when the caller
    left sqlalchemy.url empty, so setting it here is what keeps these tests
    from ever touching the real database — no environment variable involved,
    nothing another test could inherit.
    """
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    return config


@pytest.fixture(scope="session")
def migrated_database():
    """Bring the throwaway database to head once for the whole session.

    Fails loudly and early when the container is not up: without this, every
    test would instead fail with a connection error and bury the one thing the
    reader needs to know.
    """
    try:
        command.upgrade(alembic_config(), "head")
    except Exception as error:  # noqa: BLE001 - re-raised with a usable message
        raise RuntimeError(
            "Could not migrate the test database at "
            f"{TEST_DATABASE_URL}. Is it up? Run: docker compose up -d"
        ) from error
    return TEST_DATABASE_URL


@pytest_asyncio.fixture
async def engine(migrated_database):
    """An engine on the test database, with the SAME tuning as production.

    build_engine carries pool_size, pool_timeout and the lock_timeout
    connect_args, so a contention test here exercises the real configuration
    rather than a convenient one.
    """
    test_engine = build_engine(migrated_database)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def connection_handler(engine, clean_tables):  # pylint: disable=unused-argument
    """A real DatabaseConnectionHandler bound to the test database.

    Depends on clean_tables so every test that touches repositories starts from
    an empty schema; ordering between the two is what pytest resolves here.
    """
    factory = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return DatabaseConnectionHandler(session_factory=factory)


@pytest_asyncio.fixture
async def clean_tables(engine):
    """Empty every table before each test, without dropping the schema.

    TRUNCATE ... RESTART IDENTITY CASCADE is used instead of re-running the
    migrations per test: it is far faster, resets the id sequences so tests can
    assert on generated ids, and CASCADE handles the refunds -> users and
    refund_reviews -> refunds foreign keys in one statement.
    """
    async with engine.begin() as connection:
        await connection.execute(
            text("TRUNCATE refund_reviews, refunds, users RESTART IDENTITY CASCADE")
        )
    yield


@pytest.fixture
def app_uses_the_test_database(monkeypatch):
    """Points the PROCESS-WIDE connection handler at the throwaway database.

    The `engine` fixture builds its own engine, which is enough for anything
    that receives a handler by argument. Anything reaching for the module-level
    `database_connection_handler` — the app's composers, and the orphan sweep —
    needs this instead.

    It is one line only because Item 17 made the engine lazy. Built at import,
    the connection would already exist before any fixture ran.
    """
    monkeypatch.setattr(settings, "database_url", TEST_DATABASE_URL)
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    yield
    get_engine.cache_clear()
    get_session_factory.cache_clear()


@pytest.fixture
def local_storage_dirs(tmp_path, monkeypatch):
    """Sends uploads to a temp directory instead of the repository's uploads/.

    A test that leaves files in the real folder is how the seven orphans of
    2026-07 became hard to tell apart from real ones — and this is now doubly
    true, since the sweep would then find and offer to delete them.
    """
    directories = {}
    for name in ("receipts", "avatars", "payments"):
        directory = tmp_path / name
        directory.mkdir()
        monkeypatch.setitem(LOCAL_DIRECTORIES, name, str(directory))
        directories[name] = str(directory)
    return directories


@pytest.fixture
def api_client(  # pylint: disable=unused-argument
    migrated_database, clean_tables, app_uses_the_test_database, local_storage_dirs
):
    """The real FastAPI app, over HTTP, against the throwaway database.

    Everything below the HTTP layer already had integration tests (Item 19);
    what none of them touched was a ROUTE. This fixture is what Item 25 needed
    and what the project deferred twice by declining httpx: middleware, routing,
    composer, view, controller and repository all in one call.

    Repointing the app at the test database is a one-liner ONLY because Item 17
    made the engine lazy. Built at import, as it used to be, the connection
    would already exist by the time any fixture ran and this would require
    process-wide environment variables instead.
    """
    # The limiter is process-wide by design, so without this one test's
    # attempts would count against the next one and order would matter.
    rate_limiter.reset()

    with TestClient(app) as client:
        yield client


@pytest.fixture
def authenticated(api_client):
    """Registers a user and returns (client, headers, user_id).

    Through the real endpoints rather than by inserting rows: a fixture that
    reaches around the API cannot notice when registration or login break.
    """
    credentials = {"name": "Ana", "email": "api@example.com", "password": "Senha123!"}
    api_client.post("/auth/register", json=credentials)

    # The login response is FLAT — no {type, count, attributes} envelope, unlike
    # every refund response. Three envelope styles coexist in this API; see the
    # note in contract_test.py.
    body = api_client.post(
        "/auth/login", json={"email": credentials["email"], "password": credentials["password"]}
    ).json()

    return api_client, {"Authorization": f"Bearer {body['token']}"}, body["id"]


@pytest_asyncio.fixture
async def admin_headers(api_client, engine):
    """Registers a second user and promotes them, returning their auth headers.

    Promotion is a direct UPDATE because registration always creates `standard`
    (BR-003) and there is no endpoint that grants the role — the same reason
    init/promote_admin.py exists. Everything AFTER this point goes through the
    API.

    Added for Item 26: the coverage report showed every admin route at 0 — the
    payment flow, the review flow and the avatar routes had never been reached
    over HTTP by anything.
    """
    api_client.post(
        "/auth/register",
        json={"name": "Chefe", "email": "admin@example.com", "password": "Senha123!"},
    )
    async with engine.begin() as connection:
        await connection.execute(
            text("UPDATE users SET role = 'admin' WHERE email = 'admin@example.com'")
        )

    token = api_client.post(
        "/auth/login", json={"email": "admin@example.com", "password": "Senha123!"}
    ).json()["token"]

    return {"Authorization": f"Bearer {token}"}
