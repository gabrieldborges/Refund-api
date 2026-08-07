"""The migration cycle, automated.

Closes a pendency this project carried since the Alembic item: "o ciclo
upgrade/downgrade das migrations é verificado à mão. Automatizá-lo exige um
PostgreSQL descartável, que é o Item 19."

Doing this against SQLite would have been worse than not doing it — it would
hide exactly the differences the item exists to expose. Hence the throwaway
PostgreSQL, pinned to the same major version as production.

Note these tests are SYNCHRONOUS on purpose. Alembic's env.py drives its own
event loop (asyncio.run inside run_migrations_online), and calling that from
inside an already-running loop raises "asyncio.run() cannot be called from a
running event loop". So the tests stay sync and reach the database through the
small asyncio.run helpers below — which also keeps asyncpg as the only
PostgreSQL driver this project depends on, with no psycopg2 added just for
tests.
"""
import asyncio
import pytest
from sqlalchemy import inspect, text
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from src.models.settings.database_connection_handler import build_engine
from src.models.settings.metadata import metadata
from src.models.entities import users, refunds, refund_reviews  # pylint: disable=unused-import
from .conftest import TEST_DATABASE_URL, alembic_config


def run_against_test_db(operation):
    """Run a sync SQLAlchemy callable against the test database, from sync code.

    run_sync hands the callable a plain Connection, so the sync-only inspection
    APIs (inspect, compare_metadata) work unchanged over the async driver.
    """
    async def _run():
        engine = build_engine(TEST_DATABASE_URL)
        try:
            async with engine.connect() as connection:
                return await connection.run_sync(operation)
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def table_names() -> set:
    return run_against_test_db(lambda connection: set(inspect(connection).get_table_names()))


# The whole point: the schema can be built from nothing and taken apart again.
# A downgrade that was never run is a downgrade that does not work, and it is
# only ever needed in the one situation where nobody wants to debug it.
@pytest.mark.integration
def test_the_full_migration_cycle_runs_forward_and_back(migrated_database):  # pylint: disable=unused-argument
    config = alembic_config()

    command.downgrade(config, "base")
    after_downgrade = table_names()
    assert "refunds" not in after_downgrade
    assert "users" not in after_downgrade

    command.upgrade(config, "head")
    assert {"users", "refunds", "refund_reviews"} <= table_names()


# Every revision must go down as well as up, one at a time. Stepping through
# them individually catches a single broken downgrade that a straight
# "base -> head -> base" could skip over.
@pytest.mark.integration
def test_every_revision_downgrades_one_step_at_a_time(migrated_database):  # pylint: disable=unused-argument
    config = alembic_config()
    revisions = list(ScriptDirectory.from_config(config).walk_revisions())

    command.upgrade(config, "head")
    for _ in revisions:
        command.downgrade(config, "-1")

    # alembic_version survives: it is Alembic's own bookkeeping table, not part
    # of the application schema any migration created.
    assert table_names() - {"alembic_version"} == set()

    command.upgrade(config, "head")


# The schema Alembic produces must match the entity definitions. A drift here
# means someone changed a model without writing a migration, and the symptom in
# production is a column that does not exist.
@pytest.mark.integration
def test_the_migrated_schema_has_no_pending_autogenerate_diff(migrated_database):  # pylint: disable=unused-argument
    # The entity modules are imported at the top of this file for their side
    # effect: importing them is what populates `metadata` with the tables.
    # Without them the comparison would see an empty schema and report every
    # table as "should be dropped".
    def diff_against_entities(connection):
        return compare_metadata(MigrationContext.configure(connection), metadata)

    assert run_against_test_db(diff_against_entities) == []


# Migrations must leave a usable database behind, not just the right shape.
@pytest.mark.integration
def test_the_migrated_schema_accepts_a_write(migrated_database):  # pylint: disable=unused-argument
    def write_read_delete(connection):
        connection.execute(
            text(
                "INSERT INTO users (name, email, password, role) "
                "VALUES ('Ana', 'migration-check@example.com', 'x', 'standard')"
            )
        )
        stored = connection.execute(
            text("SELECT role FROM users WHERE email = 'migration-check@example.com'")
        ).scalar()
        connection.execute(
            text("DELETE FROM users WHERE email = 'migration-check@example.com'")
        )
        connection.commit()
        return stored

    assert run_against_test_db(write_read_delete) == "standard"
