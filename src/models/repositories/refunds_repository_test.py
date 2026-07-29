# pylint: disable=w0621,w0212,duplicate-code
# w0621: silences the "redefined-outer-name" warning — expected when using fixtures,
#        since the test parameter shares its name with the fixture function.
# w0212: allows access to the "protected" attribute (_mapping) of the mock, which only exists here.
# duplicate-code: this file's mock_db bootstrap (MagicMock db/session, AsyncMock execute/commit)
#        necessarily looks like users_repository_test.py's — both fake the same connection
#        protocol for a different repository. Extracting a shared fixture would couple two
#        independent test files to one mock shape for no real reuse benefit.
from unittest.mock import AsyncMock, MagicMock
import pytest
from .refunds_repository import RefundsRepository


# Fixture: builds a fake database (mock) with the default behavior expected by most
# tests. Each test gets a fresh instance (isolation), so one test can't contaminate
# another. MagicMock creates an object that accepts any attribute/method; here we only
# configure what the repository actually uses: session.execute/commit.
@pytest.fixture
def mock_db():
    db = MagicMock()
    execute_result = MagicMock()
    # Simulates the return of an INSERT: SQLAlchemy exposes the generated PK here.
    execute_result.inserted_primary_key = [1]
    # AsyncMock because in the real code these methods are called with "await".
    db.session.execute = AsyncMock(return_value=execute_result)
    db.session.commit = AsyncMock()
    return db


# Verifies inserting a refund returns the generated id and commits the transaction.
# AAA pattern (Arrange-Act-Assert): set up -> execute -> verify.
@pytest.mark.asyncio
async def test_insert_refund_returns_the_new_id(mock_connection, mock_db):
    # Arrange: create the repository wired to the fake connection.
    repository = RefundsRepository(mock_connection)

    # Act: run the operation under test.
    refund_info = {
        "user_id": 1, "name": "Ana", "category": "food",
        "amount_in_cents": 1000, "filename": "receipt.jpg"
    }
    refund_id = await repository.insert_refund(refund_info)

    # Assert: the returned id came from the simulated PK, and INSERT + commit happened
    # exactly once (guarantees we actually saved to the database).
    assert refund_id == 1
    mock_db.session.execute.assert_awaited_once()
    mock_db.session.commit.assert_awaited_once()


# Verifies the listing returns the items (already converted to dict), the total count,
# and the total amount in cents.
@pytest.mark.asyncio
async def test_select_refunds_returns_items_total_and_sum(mock_connection, mock_db):
    # Arrange: simulate a database row. In SQLAlchemy Core, each row has _mapping,
    # which behaves like a column->value dict; the repository converts that into a dict.
    row = MagicMock()
    row._mapping = {"id": 1, "user_id": 1, "name": "Ana"}
    fetch_result = MagicMock()
    fetch_result.fetchall = MagicMock(return_value=[row])
    # count() and sum() now share a single query, so its result exposes .one() ->
    # a (total, total_amount) tuple, instead of the old scalar() COUNT result.
    totals_result = MagicMock()
    totals_result.one = MagicMock(return_value=(1, 1000))
    # select_refunds calls session.execute twice (totals query, then rows query), so
    # a single shared return_value can't serve both calls; side_effect supplies one
    # result per call, in order.
    mock_db.session.execute = AsyncMock(side_effect=[totals_result, fetch_result])

    repository = RefundsRepository(mock_connection)
    refunds, total, total_amount = await repository.select_refunds(page=1, per_page=10, user_id=1)

    assert total == 1
    assert total_amount == 1000
    assert refunds == [{"id": 1, "user_id": 1, "name": "Ana"}]


# The sum must cover every refund matching the filter, not just the page that
# was returned, and an empty result set must read as 0 rather than None.
@pytest.mark.asyncio
async def test_select_refunds_returns_zero_sum_when_there_are_no_rows(mock_connection, mock_db):
    # SUM over an empty set comes back as NULL from the database, i.e. None here.
    totals_result = MagicMock()
    totals_result.one = MagicMock(return_value=(0, None))
    fetch_result = MagicMock()
    fetch_result.fetchall = MagicMock(return_value=[])
    mock_db.session.execute = AsyncMock(side_effect=[totals_result, fetch_result])

    repository = RefundsRepository(mock_connection)
    _, total, total_amount = await repository.select_refunds(page=1, per_page=10)

    assert total == 0
    assert total_amount == 0


# Happy path: looking up an existing id returns the refund as a dict.
@pytest.mark.asyncio
async def test_select_refund_by_id_found(mock_connection, mock_db):
    row = MagicMock()
    row._mapping = {"id": 1, "name": "Ana"}
    result = MagicMock()
    # fetchone returns a row -> refund found.
    result.fetchone = MagicMock(return_value=row)
    mock_db.session.execute = AsyncMock(return_value=result)

    repository = RefundsRepository(mock_connection)
    refund = await repository.select_refund_by_id(1)

    assert refund == {"id": 1, "name": "Ana"}


# "Not found" path: when the database returns no row, the method returns None.
@pytest.mark.asyncio
async def test_select_refund_by_id_not_found(mock_connection, mock_db):
    result = MagicMock()
    # fetchone returns None -> nothing found.
    result.fetchone = MagicMock(return_value=None)
    mock_db.session.execute = AsyncMock(return_value=result)

    repository = RefundsRepository(mock_connection)
    refund = await repository.select_refund_by_id(999)

    assert refund is None


# Verifies deleting runs the DELETE and commits the transaction, and that
# rowcount is returned so the caller can tell "deleted" from "not eligible".
@pytest.mark.asyncio
async def test_delete_refund(mock_connection, mock_db):
    execute_result = MagicMock()
    execute_result.rowcount = 1
    mock_db.session.execute = AsyncMock(return_value=execute_result)

    repository = RefundsRepository(mock_connection)
    deleted_count = await repository.delete_refund(1)

    mock_db.session.execute.assert_awaited_once()
    mock_db.session.commit.assert_awaited_once()
    assert deleted_count == 1


# The DELETE must be conditional on status, not just id: this is what closes the
# race with a concurrent review that moves the refund out of "pending" between
# the controller's read and this delete. Mirrors how
# refund_status_repository_test.py asserts on "FOR UPDATE" by inspecting the
# emitted statement's string form.
@pytest.mark.asyncio
async def test_delete_refund_filters_on_pending_status(mock_connection, mock_db):
    execute_result = MagicMock()
    execute_result.rowcount = 0
    mock_db.session.execute = AsyncMock(return_value=execute_result)

    repository = RefundsRepository(mock_connection)
    deleted_count = await repository.delete_refund(1)

    statement = str(mock_db.session.execute.call_args[0][0])
    assert "status" in statement
    assert deleted_count == 0
