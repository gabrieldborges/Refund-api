# pylint: disable=w0621,w0212
# w0212: needed to reach the repositories' name-mangled private __session
# attribute directly, which is how the shared-session test proves identity.
from unittest.mock import AsyncMock, MagicMock
import pytest
from .unit_of_work import UnitOfWork


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_connection(mock_session):
    connection = MagicMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=mock_session)
    context.__aexit__ = AsyncMock(return_value=None)
    connection.connect = MagicMock(return_value=context)
    return connection


# Both repositories must share the SAME session — that is the entire mechanism
# by which their writes end up in one transaction. Asserting only
# execute.await_count == 2 cannot fail: a broken UnitOfWork that called
# connect() twice (giving each repository its OWN session) would still hit
# execute twice on mocks that return the same objects regardless. So we also
# pin that connect() was called exactly once and that both repositories hold
# the identical session object.
@pytest.mark.asyncio
async def test_both_repositories_share_the_same_session(mock_connection, mock_session):
    async with UnitOfWork(mock_connection) as unit_of_work:
        await unit_of_work.refunds.update_status(1, "approved")
        await unit_of_work.reviews.insert_review(
            refund_id=1, reviewer_id=9, from_status="pending", to_status="approved", reason=None
        )

    assert mock_session.execute.await_count == 2
    assert mock_connection.connect.call_count == 1
    assert unit_of_work.refunds._RefundStatusRepository__session \
        is unit_of_work.reviews._RefundReviewsRepository__session


@pytest.mark.asyncio
async def test_commit_commits_the_session(mock_connection, mock_session):
    async with UnitOfWork(mock_connection) as unit_of_work:
        await unit_of_work.commit()

    mock_session.commit.assert_awaited_once()


# The safety property: an exception inside the block rolls back, so a partial
# write can never survive.
@pytest.mark.asyncio
async def test_an_exception_inside_the_block_rolls_back(mock_connection, mock_session):
    with pytest.raises(ValueError):
        async with UnitOfWork(mock_connection) as unit_of_work:
            await unit_of_work.refunds.update_status(1, "approved")
            raise ValueError("boom")

    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_awaited()


# Leaving the block without committing must not persist anything. The failure
# mode is "nothing was written", never "half was written".
@pytest.mark.asyncio
async def test_leaving_without_commit_does_not_commit(mock_connection, mock_session):
    async with UnitOfWork(mock_connection) as unit_of_work:
        await unit_of_work.refunds.update_status(1, "approved")

    mock_session.commit.assert_not_awaited()


# The pool has pool_size=2, max_overflow=0: if a failing rollback ever skipped
# closing the session, its connection would never return to the pool, and two
# of these would hang the whole API. The session must be closed regardless.
@pytest.mark.asyncio
async def test_the_session_is_closed_even_when_rollback_fails(mock_connection, mock_session):
    mock_session.rollback = AsyncMock(side_effect=RuntimeError("rollback failed"))
    context = mock_connection.connect.return_value

    with pytest.raises(RuntimeError):
        async with UnitOfWork(mock_connection) as unit_of_work:
            await unit_of_work.refunds.update_status(1, "approved")
            raise ValueError("boom")

    context.__aexit__.assert_awaited_once()
