# pylint: disable=w0621
# w0621: the mock_repository parameter reuses the fixture's name (standard pytest pattern).
from unittest.mock import AsyncMock, MagicMock
import pytest
from .user_register_controller import UserRegisterController


# Fake repository: insert_user just returns id 1, without touching a database. This keeps
# the test focused on the controller's LOGIC (password hashing, forcing the role, response shape).
@pytest.fixture
def mock_repository():
    mock_repo = MagicMock()
    mock_repo.insert_user = AsyncMock(return_value=1)
    return mock_repo


# Happy path: registration returns the user with role "standard" and WITHOUT exposing the password.
@pytest.mark.asyncio
async def test_register_creates_a_user_with_standard_role(mock_repository):
    user_data = {"name": "Gabriel", "email": "gabriel@example.com", "password": "senha12345"}
    controller = UserRegisterController(mock_repository)

    response = await controller.register(user_data)

    assert response["type"] == "User"
    assert response["attributes"]["id"] == 1
    assert response["attributes"]["email"] == "gabriel@example.com"
    assert response["attributes"]["role"] == "standard"
    # The password (even hashed) must never come back in the API response.
    assert "password" not in response["attributes"]


# Security: the password must be persisted as a hash, never as plain text.
@pytest.mark.asyncio
async def test_register_stores_a_hashed_password_not_the_plain_text(mock_repository):
    user_data = {"name": "Gabriel", "email": "gabriel@example.com", "password": "senha12345"}
    controller = UserRegisterController(mock_repository)

    await controller.register(user_data)

    # Inspect what the controller passed to the repository: await_args.args[0] is the
    # 1st positional argument of the insert_user call. The password there must NOT be the raw text.
    inserted = mock_repository.insert_user.await_args.args[0]
    assert inserted["password"] != "senha12345"


# Security: even if the client sends role "admin", the server forces "standard".
# Prevents self-promotion to admin through registration.
@pytest.mark.asyncio
async def test_register_ignores_any_role_sent_by_the_client(mock_repository):
    user_data = {
        "name": "Gabriel", "email": "gabriel@example.com",
        "password": "senha12345", "role": "admin"
    }
    controller = UserRegisterController(mock_repository)

    await controller.register(user_data)

    inserted = mock_repository.insert_user.await_args.args[0]
    assert inserted["role"] == "standard"
