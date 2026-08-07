# These are revert-nets, not behaviour tests: they read back what we
# configured, so an accidental revert shows up red instead of as a 500 under
# concurrency months later. They CANNOT catch a connect_args shape the driver
# rejects — asking PostgreSQL itself is the behavioural half, still manual.
#
# The private attributes are unavoidable: SQLAlchemy's pool exposes size()
# publicly but has no public accessor for max_overflow, pre_ping or recycle.
#
# These used to import the module-level `engine`, which meant this file could
# only run with a parseable DATABASE_URL in the environment. Now they build an
# engine from an explicit URL: the pool tuning is what is under test, and it has
# nothing to do with which database the application happens to point at.
from src.models.settings.database_connection_handler import build_engine


TEST_URL = "postgresql+asyncpg://test:test@localhost:5432/test"


def test_pool_is_sized_for_more_than_two_concurrent_operations():
    engine = build_engine(TEST_URL)

    assert engine.pool.size() == 5
    # SQLAlchemy exposes the overflow ceiling as a private attribute; there is
    # no public accessor for it.
    assert engine.pool._max_overflow == 10  # pylint: disable=protected-access


def test_dead_connections_are_discarded_before_use():
    # Neon suspends idle compute and drops connections. Without pre-ping the
    # pool hands out a socket the server already closed, and the symptom is
    # characteristic: the first request after an idle period fails, the next
    # one works.
    engine = build_engine(TEST_URL)

    assert engine.pool._pre_ping is True  # pylint: disable=protected-access


def test_idle_connections_are_recycled_before_neon_drops_them():
    # This is the Neon idle-connection fix: recycling a pooled connection
    # after 300s keeps it from going stale under Neon's own idle timeout. A
    # revert of this value would not show up as a test failure anywhere else
    # — only as an intermittent 500 under production concurrency, months
    # later. That is exactly what this revert-net exists to catch instead.
    engine = build_engine(TEST_URL)

    assert engine.pool._recycle == 300  # pylint: disable=protected-access


def test_a_connection_wait_gives_up_instead_of_blocking_forever():
    # How long a caller waits for a pooled connection before failing, once
    # pool_size + max_overflow are all checked out.
    engine = build_engine(TEST_URL)

    assert engine.pool._timeout == 10  # pylint: disable=protected-access


# No revert-net for connect_args / lock_timeout, deliberately: SQLAlchemy only
# applies connect_args when a connection is actually opened, so an engine that
# never connects exposes them nowhere reachable. Tried and abandoned rather than
# reached for through pool internals. The proof for that setting stays what it
# already was — a manual SHOW lock_timeout against the real database.
