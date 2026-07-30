# These are revert-nets, not behaviour tests: they read back what we
# configured, so an accidental revert shows up red instead of as a 500 under
# concurrency months later. They CANNOT catch a connect_args shape the driver
# rejects — Step 5 asks PostgreSQL itself, which is the behavioural half.
#
# The private attributes are unavoidable: SQLAlchemy's pool exposes size()
# publicly but has no public accessor for max_overflow, pre_ping or recycle.
from src.models.settings.database_connection_handler import engine


def test_pool_is_sized_for_more_than_two_concurrent_operations():
    assert engine.pool.size() == 5
    # SQLAlchemy exposes the overflow ceiling as a private attribute; there is
    # no public accessor for it.
    assert engine.pool._max_overflow == 10  # pylint: disable=protected-access


def test_dead_connections_are_discarded_before_use():
    # Neon suspends idle compute and drops connections. Without pre-ping the
    # pool hands out a socket the server already closed, and the symptom is
    # characteristic: the first request after an idle period fails, the next
    # one works.
    assert engine.pool._pre_ping is True  # pylint: disable=protected-access
