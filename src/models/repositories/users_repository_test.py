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


# Removing the picture is an update to NULL, not a delete: the user row stays.
@pytest.mark.asyncio
async def test_update_avatar_accepts_none_to_clear_the_picture(mock_connection, mock_db):
    repository = UsersRepository(mock_connection)

    await repository.update_avatar(7, None)

    statement = str(mock_db.session.execute.call_args[0][0])
    assert "UPDATE users" in statement
    mock_db.session.commit.assert_awaited_once()
