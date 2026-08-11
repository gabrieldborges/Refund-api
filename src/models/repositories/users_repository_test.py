# pylint: disable=w0621,w0212
# w0621: fixtures share a name with the test parameter (standard pytest pattern).
# w0212: access to the "protected" _mapping attribute of the row mock.
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy.exc import IntegrityError
from .users_repository import UsersRepository


# Fake database for the happy path. Note mock_connection (in conftest.py) depends on
# this fixture: since mock_db is defined here, this is the mock_db that gets injected there.
@pytest.fixture
def mock_db():
    db = MagicMock()
    execute_result = MagicMock()
    execute_result.inserted_primary_key = [1]
    db.session.execute = AsyncMock(return_value=execute_result)
    db.session.commit = AsyncMock()
    db.session.rollback = AsyncMock()
    return db


# Fake database for the error path: here we use side_effect instead of return_value.
# side_effect with an exception makes the mock RAISE that exception when called, simulating
# SQLAlchemy blowing up with IntegrityError when the email's UNIQUE constraint is violated.
@pytest.fixture
def mock_db_raise_integrity_error():
    db = MagicMock()
    db.session.execute = AsyncMock(side_effect=IntegrityError("statement", "params", "orig"))
    db.session.commit = AsyncMock()
    db.session.rollback = AsyncMock()
    return db


# Connection whose connect() yields the session that raises. We need our own fixture
# here because conftest's mock_connection is wired to the "happy" mock_db.
@pytest.fixture
def mock_connection_error(mock_db_raise_integrity_error):
    connection = MagicMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=mock_db_raise_integrity_error.session)
    context.__aexit__ = AsyncMock(return_value=None)
    connection.connect = MagicMock(return_value=context)
    return connection


# Happy path for registration: returns the id and commits, no rollback needed.
@pytest.mark.asyncio
async def test_insert_user_returns_the_new_id(mock_connection, mock_db):
    repository = UsersRepository(mock_connection)

    user_info = {"name": "Gabriel", "email": "gabriel@example.com", "password": "hashed", "role": "standard"}
    user_id = await repository.insert_user(user_info)

    assert user_id == 1
    mock_db.session.execute.assert_awaited_once()
    mock_db.session.commit.assert_awaited_once()
    # assert_not_awaited: since everything went fine, rollback must never be called.
    mock_db.session.rollback.assert_not_awaited()


# Error path: a duplicate email must turn into a clear message and roll back the transaction.
@pytest.mark.asyncio
async def test_insert_user_when_email_already_exists(mock_connection_error, mock_db_raise_integrity_error):
    repository = UsersRepository(mock_connection_error)

    user_info = {"name": "Gabriel", "email": "gabriel@example.com", "password": "hashed", "role": "standard"}

    # pytest.raises: asserts the block MUST raise the exception; if it doesn't, the test fails.
    # The "as e" captures the exception so we can inspect its message afterwards.
    with pytest.raises(Exception) as e:
        await repository.insert_user(user_info)

    # On failure, the repository must call rollback to avoid leaving a half-done transaction.
    mock_db_raise_integrity_error.session.rollback.assert_awaited_once()
    # And it must translate the low-level database error into a friendly message.
    assert str(e.value) == "Email already registered"


# Looking up an existing email returns the user as a dict.
@pytest.mark.asyncio
async def test_select_user_by_email_found(mock_connection, mock_db):
    row = MagicMock()
    row._mapping = {"id": 1, "name": "Gabriel", "email": "gabriel@example.com"}
    result = MagicMock()
    result.fetchone = MagicMock(return_value=row)
    mock_db.session.execute = AsyncMock(return_value=result)

    repository = UsersRepository(mock_connection)
    user = await repository.select_user_by_email("gabriel@example.com")

    assert user == {"id": 1, "name": "Gabriel", "email": "gabriel@example.com"}


# Looking up a nonexistent email returns None (important for the login flow).
@pytest.mark.asyncio
async def test_select_user_by_email_not_found(mock_connection, mock_db):
    result = MagicMock()
    result.fetchone = MagicMock(return_value=None)
    mock_db.session.execute = AsyncMock(return_value=result)

    repository = UsersRepository(mock_connection)
    user = await repository.select_user_by_email("missing@example.com")

    assert user is None


# Looking up an existing id returns the user as a dict.
@pytest.mark.asyncio
async def test_select_user_by_id_found(mock_connection, mock_db):
    row = MagicMock()
    row._mapping = {"id": 1, "name": "Gabriel"}
    result = MagicMock()
    result.fetchone = MagicMock(return_value=row)
    mock_db.session.execute = AsyncMock(return_value=result)

    repository = UsersRepository(mock_connection)
    user = await repository.select_user_by_id(1)

    assert user == {"id": 1, "name": "Gabriel"}


# Updating avatar persists the filename to the database.
@pytest.mark.asyncio
async def test_update_avatar_persists_the_filename(mock_connection, mock_db):
    repository = UsersRepository(mock_connection)

    await repository.update_avatar(7, "abc.jpg")

    mock_db.session.execute.assert_awaited_once()
    mock_db.session.commit.assert_awaited_once()
    # Verify the bound parameters: filename set correctly and WHERE clause targets right user.
    statement = mock_db.session.execute.call_args[0][0]
    params = statement.compile().params
    assert params["avatar_filename"] == "abc.jpg"
    assert params["id_1"] == 7


# Removing the picture is an update to NULL, not a delete: the user row stays.
@pytest.mark.asyncio
async def test_update_avatar_accepts_none_to_clear_the_picture(mock_connection, mock_db):
    repository = UsersRepository(mock_connection)

    await repository.update_avatar(7, None)

    # Verify the UPDATE statement was issued and committed.
    mock_db.session.execute.assert_awaited_once()
    mock_db.session.commit.assert_awaited_once()
    # Verify the bound parameters: avatar_filename is None (not empty string or other falsy).
    statement = mock_db.session.execute.call_args[0][0]
    params = statement.compile().params
    assert params["avatar_filename"] is None
    assert params["id_1"] == 7


# select_users runs TWO queries in one session: the count first, then the page.
# This helper wires the session to answer them in that order, so each test can
# reach either statement by index.
def _wire_select_users(mock_db, rows, total):
    count_result = MagicMock()
    count_result.scalar_one = MagicMock(return_value=total)
    page_result = MagicMock()
    page_result.fetchall = MagicMock(return_value=rows)
    mock_db.session.execute = AsyncMock(side_effect=[count_result, page_result])


def _user_row(user_id, name):
    row = MagicMock()
    row._mapping = {
        "id": user_id,
        "name": name,
        "email": f"{name}@example.com",
        "password": "hashed",
        "role": "standard",
        "avatar_filename": None,
        "created_at": None,
    }
    return row


def _count_statement(mock_db):
    return str(mock_db.session.execute.call_args_list[0][0][0])


def _page_statement(mock_db):
    return str(mock_db.session.execute.call_args_list[1][0][0])


# The page comes back as plain dicts because the serializer indexes them by key.
@pytest.mark.asyncio
async def test_select_users_returns_the_rows_as_dicts_and_the_total(mock_connection, mock_db):
    _wire_select_users(mock_db, [_user_row(1, "ana"), _user_row(2, "bruno")], total=2)

    users, total = await UsersRepository(mock_connection).select_users(page=1, per_page=10)

    assert total == 2
    assert [user["name"] for user in users] == ["ana", "bruno"]
    assert isinstance(users[0], dict)


@pytest.mark.asyncio
async def test_select_users_pages_with_limit_and_offset(mock_connection, mock_db):
    _wire_select_users(mock_db, [], total=0)

    await UsersRepository(mock_connection).select_users(page=3, per_page=10)

    statement = mock_db.session.execute.call_args_list[1][0][0]
    assert "LIMIT" in str(statement) and "OFFSET" in str(statement)
    params = statement.compile().params
    assert params["param_1"] == 10
    assert params["param_2"] == 20


# Two ordering keys, not one. PostgreSQL guarantees no order among rows whose
# sort key ties, so with LIMIT/OFFSET a tie can show one row on two pages while
# another never appears at all. Namesakes are ordinary, so this tie is not
# hypothetical — same reasoning as RefundsRepository.__order_by.
@pytest.mark.asyncio
async def test_select_users_orders_by_name_with_id_as_the_tiebreaker(mock_connection, mock_db):
    _wire_select_users(mock_db, [], total=0)

    await UsersRepository(mock_connection).select_users(page=1, per_page=10)

    assert "ORDER BY users.name ASC, users.id ASC" in _page_statement(mock_db)


# ilike renders as lower(...) LIKE lower(...), which is the case-insensitive
# partial match the Home's refund search already uses.
@pytest.mark.asyncio
async def test_select_users_filters_by_partial_name(mock_connection, mock_db):
    _wire_select_users(mock_db, [], total=0)

    await UsersRepository(mock_connection).select_users(page=1, per_page=10, name="an")

    statement = mock_db.session.execute.call_args_list[1][0][0]
    assert "lower(users.name) LIKE lower" in str(statement)
    assert statement.compile().params["name_1"] == "%an%"


# A count that ignored the filter would make total_pages promise pages the page
# query can never fill.
@pytest.mark.asyncio
async def test_select_users_counts_with_the_same_filter_as_the_page(mock_connection, mock_db):
    _wire_select_users(mock_db, [], total=0)

    await UsersRepository(mock_connection).select_users(page=1, per_page=10, name="an")

    assert "lower(users.name) LIKE lower" in _count_statement(mock_db)


# An empty string is not a search: it must not become LIKE '%%', which would
# read as a filter in the SQL while matching everything.
@pytest.mark.asyncio
async def test_select_users_treats_an_empty_name_as_no_filter(mock_connection, mock_db):
    _wire_select_users(mock_db, [], total=0)

    await UsersRepository(mock_connection).select_users(page=1, per_page=10, name="")

    assert "LIKE" not in _page_statement(mock_db)
    assert "LIKE" not in _count_statement(mock_db)


# The password column is still selected — the repository's job is the row, and
# keeping it out of responses is user_serializer's. This test pins that split so
# nobody "fixes" it in the wrong layer.
@pytest.mark.asyncio
async def test_select_users_returns_the_whole_row_including_the_hash(mock_connection, mock_db):
    _wire_select_users(mock_db, [_user_row(1, "ana")], total=1)

    users, _ = await UsersRepository(mock_connection).select_users(page=1, per_page=10)

    assert users[0]["password"] == "hashed"
