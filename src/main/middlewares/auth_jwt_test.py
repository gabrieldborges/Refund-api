# get_current_user is the FastAPI dependency that reads the Authorization header,
# validates the JWT, and returns the user. We test the 4 scenarios that matter for
# security: a valid token (happy path) and three forms of invalid input. No fixtures
# here: each test builds its own header, and we use the real JwtHandler to generate genuine tokens.
import pytest
from src.drivers.jwt_handler import JwtHandler
from src.errors.types.http_unauthorized_error import HttpUnauthorizedError
from .auth_jwt import get_current_user


# Happy path: a "Bearer <valid token>" header is accepted and returns the payload's data.
@pytest.mark.asyncio
async def test_get_current_user_with_a_valid_token():
    token = JwtHandler().create_jwt_token({"user_id": 1, "role": "standard"})

    user = await get_current_user(authorization=f"Bearer {token}")

    assert user["user_id"] == 1
    assert user["role"] == "standard"


# No header (None) -> 401 unauthorized. Anonymous requests are blocked.
@pytest.mark.asyncio
async def test_get_current_user_without_header_raises_unauthorized():
    with pytest.raises(HttpUnauthorizedError):
        await get_current_user(authorization=None)


# Header in the wrong format (missing the "Bearer " prefix) -> 401.
@pytest.mark.asyncio
async def test_get_current_user_with_malformed_header_raises_unauthorized():
    with pytest.raises(HttpUnauthorizedError):
        await get_current_user(authorization="NotBearerFormat")


# Right format, but an invalid/forged token -> 401 (the signature doesn't match).
@pytest.mark.asyncio
async def test_get_current_user_with_an_invalid_token_raises_unauthorized():
    with pytest.raises(HttpUnauthorizedError):
        await get_current_user(authorization="Bearer not-a-real-token")
