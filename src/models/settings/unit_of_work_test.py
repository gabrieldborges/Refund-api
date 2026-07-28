# pylint: disable=w0621
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
# by which their writes end up in one transaction.
@pytest.mark.asyncio
async def test_both_repositories_share_the_same_session(mock_connection, mock_session):
    async with UnitOfWork(mock_connection) as unit_of_work:
        await unit_of_work.refunds.update_status(1, "approved")
        await unit_of_work.reviews.insert_review(
            refund_id=1, reviewer_id=9, from_status="pending", to_status="approved", reason=None
        )

    assert mock_session.execute.await_count == 2


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
