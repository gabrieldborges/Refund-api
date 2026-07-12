# pylint: disable=w0621,w0212
# w0621: silences the "redefined-outer-name" warning — expected when using fixtures,
#        since the test parameter shares its name with the fixture function.
# w0212: allows access to the "protected" attribute (_mapping) of the mock, which only exists here.
from unittest.mock import AsyncMock, MagicMock
import pytest
from .refunds_repository import RefundsRepository


# Fixture: builds a fake database (mock) with the default behavior expected by most
# tests. Each test gets a fresh instance (isolation), so one test can't contaminate
# another. MagicMock creates an object that accepts any attribute/method; here we only
# configure what the repository actually uses: session.execute/scalar/commit.
@pytest.fixture
def mock_db():
    db = MagicMock()
    execute_result = MagicMock()
    # Simulates the return of an INSERT: SQLAlchemy exposes the generated PK here.
    execute_result.inserted_primary_key = [1]
    # AsyncMock because in the real code these methods are called with "await".
    db.session.execute = AsyncMock(return_value=execute_result)
    db.session.scalar = AsyncMock(return_value=0)
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


# Verifies the listing returns both the items (already converted to dict) and the total.
@pytest.mark.asyncio
async def test_select_refunds_returns_items_and_total(mock_connection, mock_db):
    # Arrange: simulate a database row. In SQLAlchemy Core, each row has _mapping,
    # which behaves like a column->value dict; the repository converts that into a dict.
    row = MagicMock()
    row._mapping = {"id": 1, "user_id": 1, "name": "Ana"}
    fetch_result = MagicMock()
    fetch_result.fetchall = MagicMock(return_value=[row])
    # Overrides the fixture's default for this scenario: execute returns the rows,
    # and scalar (the total COUNT) returns 1.
    mock_db.session.execute = AsyncMock(return_value=fetch_result)
    mock_db.session.scalar = AsyncMock(return_value=1)

    repository = RefundsRepository(mock_connection)
    refunds, total = await repository.select_refunds(page=1, per_page=10, user_id=1)

    assert total == 1
    assert refunds == [{"id": 1, "user_id": 1, "name": "Ana"}]


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


# Verifies deleting runs the DELETE and commits the transaction.
# There's no return value to check, so we validate behavior through the mocks.
@pytest.mark.asyncio
async def test_delete_refund(mock_connection, mock_db):
    repository = RefundsRepository(mock_connection)
    await repository.delete_refund(1)

    mock_db.session.execute.assert_awaited_once()
    mock_db.session.commit.assert_awaited_once()
