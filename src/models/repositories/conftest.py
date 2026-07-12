# conftest.py is a special pytest file: any fixture defined here is automatically
# available to ALL tests in this directory (and subfolders), with no import needed.
# It's the right place for fixtures that repeat across multiple test files in the
# same package.
#
# A "fixture" is a function that prepares an object/state ready for a test to use.
# A test "asks for" a fixture just by declaring a parameter with the same name;
# pytest runs the fixture and injects its return value into that parameter.
from unittest.mock import AsyncMock, MagicMock
import pytest


# Simulates the database connection's "async context manager" — the object used
# in the repository as "async with self.__db_connection as database: ...".
# Note this fixture asks for another fixture as a parameter (mock_db): pytest resolves
# that chain automatically. Since mock_db is defined in each test file, each one
# supplies its own, and this mock_connection only handles the "with" protocol.
@pytest.fixture
def mock_connection(mock_db):
    connection = MagicMock()
    # __aenter__ is what "async with" calls on entering the block; we return mock_db,
    # so inside the "with" the code sees the fake database. AsyncMock is a mock whose
    # return value can be "await"-ed (used for async functions/methods).
    connection.__aenter__ = AsyncMock(return_value=mock_db)
    # __aexit__ is called on exiting the block; returning None means "don't suppress exceptions".
    connection.__aexit__ = AsyncMock(return_value=None)
    return connection
