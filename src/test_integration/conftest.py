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
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config
from src.models.settings.database_connection_handler import (
    DatabaseConnectionHandler,
    build_engine,
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
