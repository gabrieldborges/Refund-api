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


# Fixture: a fake db object exposing a mocked session, matching the shape the
# mark_as_paid tests below expect (mock_db.session), distinct from mock_session
# used by the tests above (which pass the session directly to the repository).
@pytest.fixture
def mock_db():
    db = MagicMock()
    db.session.execute = AsyncMock()
    db.session.commit = AsyncMock()
    return db


# The UPDATE is conditional on status='approved' so the database itself refuses
# a second concurrent payment. This is deliberately NOT select_for_update: a
# lock would hold a pool connection while waiting, which is the documented
# pendency this cycle avoids making worse.
@pytest.mark.asyncio
async def test_mark_as_paid_only_touches_a_refund_still_approved(mock_db):
    mock_db.session.execute = AsyncMock(return_value=MagicMock(rowcount=1))
    repository = RefundStatusRepository(mock_db.session)

    affected = await repository.mark_as_paid(1, "receipt.pdf")

    assert affected == 1
    mock_db.session.execute.assert_awaited_once()


# Zero rows means someone else paid first between our guard check and this
# UPDATE. The controller turns that into a 422 and deletes the file it had
# already written.
@pytest.mark.asyncio
async def test_mark_as_paid_reports_zero_when_the_status_already_changed(mock_db):
    mock_db.session.execute = AsyncMock(return_value=MagicMock(rowcount=0))
    repository = RefundStatusRepository(mock_db.session)

    affected = await repository.mark_as_paid(1, "receipt.pdf")

    assert affected == 0
