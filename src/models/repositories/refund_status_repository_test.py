# pylint: disable=w0621,w0212
# w0212: allows access to the "protected" attribute (_mapping) of the mock, which only exists here.
from unittest.mock import AsyncMock, MagicMock
import pytest
from .refund_status_repository import RefundStatusRepository


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


# The row is read with FOR UPDATE so a concurrent reviewer blocks until this
# transaction ends, instead of deciding from a stale status.
@pytest.mark.asyncio
async def test_select_for_update_locks_the_row_and_returns_a_dict(mock_session):
    row = MagicMock()
    row._mapping = {"id": 1, "user_id": 7, "status": "pending"}
    mock_session.execute.return_value.fetchone = MagicMock(return_value=row)

    repository = RefundStatusRepository(mock_session)
    refund = await repository.select_for_update(1)

    assert refund == {"id": 1, "user_id": 7, "status": "pending"}
    statement = str(mock_session.execute.call_args[0][0])
    assert "FOR UPDATE" in statement


@pytest.mark.asyncio
async def test_select_for_update_returns_none_when_the_refund_does_not_exist(mock_session):
    mock_session.execute.return_value.fetchone = MagicMock(return_value=None)

    repository = RefundStatusRepository(mock_session)

    assert await repository.select_for_update(999) is None


# The repository must NOT commit: the UnitOfWork owns that decision, and a commit
# here would defeat the whole point of the transaction boundary.
@pytest.mark.asyncio
async def test_update_status_executes_without_committing(mock_session):
    repository = RefundStatusRepository(mock_session)

    await repository.update_status(1, "approved")

    mock_session.execute.assert_awaited_once()
    mock_session.commit.assert_not_awaited()
