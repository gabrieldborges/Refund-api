# pylint: disable=w0621
# w0621: test parameters reuse the fixtures' names (standard pytest pattern).
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.drivers.password_handler import PasswordHandler
from src.errors.types.http_bad_request_error import HttpBadRequestError
from .user_login_controller import UserLoginController


# Fixture with a REAL password hash. We intentionally don't mock PasswordHandler here:
# we want the controller's check_password to compare against a genuine hash, otherwise
# the "correct login" test wouldn't prove anything. Fixtures can also compute derived values like this.
@pytest.fixture
def hashed_password():
    return PasswordHandler().encrypt_password("senha12345")


# Fake repository that returns an existing user (with the password already hashed).
# Depends on the hashed_password fixture: pytest resolves the chain and injects the hash here.
@pytest.fixture
def mock_repository(hashed_password):
    mock_repo = MagicMock()
    mock_repo.select_user_by_email = AsyncMock(return_value={
        "id": 1, "name": "Gabriel", "email": "gabriel@example.com",
        "password": hashed_password, "role": "standard",
        "avatar_filename": "gabriel.png"
    })
    return mock_repo


# Happy path: correct credentials grant access and return a token (string).
@pytest.mark.asyncio
async def test_login_with_correct_credentials_returns_a_token(mock_repository):
    controller = UserLoginController(mock_repository)

    response = await controller.login({"email": "gabriel@example.com", "password": "senha12345"})

    assert response["access"] is True
    assert response["role"] == "standard"
    # We don't check the token's exact value (it varies); just its type/contract.
    assert isinstance(response["token"], str)


# Wrong password: user exists, but the hash doesn't match -> generic "Invalid credentials" error.
@pytest.mark.asyncio
async def test_login_with_wrong_password_raises_bad_request(mock_repository):
    controller = UserLoginController(mock_repository)

    with pytest.raises(HttpBadRequestError) as e:
        await controller.login({"email": "gabriel@example.com", "password": "wrong"})

    assert str(e.value) == "Invalid credentials"


# Unknown email: this test does NOT use the mock_repository fixture because it needs a
# repository that returns None. The message must be IDENTICAL to the wrong-password case —
# for security, we never reveal whether it was the email or the password that was wrong.
@pytest.mark.asyncio
async def test_login_with_unknown_email_raises_the_same_generic_error():
    mock_repo = MagicMock()
    mock_repo.select_user_by_email = AsyncMock(return_value=None)
    controller = UserLoginController(mock_repo)

    with pytest.raises(HttpBadRequestError) as e:
        await controller.login({"email": "missing@example.com", "password": "whatever"})

    assert str(e.value) == "Invalid credentials"


# The sidebar needs the picture right after login. Additive and safe in both
# directions: the frontend's Zod drops unknown keys, so an old client ignores it.
# The fixture's user carries a real filename (not None) and we assert the exact
# value, so a controller that hardcoded the key to None would fail this test.
@pytest.mark.asyncio
async def test_login_response_includes_the_avatar_filename(mock_repository):
    controller = UserLoginController(mock_repository)

    response = await controller.login({"email": "gabriel@example.com", "password": "senha12345"})

    assert response["avatar_filename"] == "gabriel.png"
