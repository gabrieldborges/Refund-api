# pylint: disable=w0621
# w0621: the mock_controller parameter reuses the fixture's name (standard pytest pattern).
from unittest.mock import MagicMock, AsyncMock
import pytest
from fastapi import HTTPException
from src.views.http_types.http_request import HttpRequest
from src.errors.types.http_bad_request_error import HttpBadRequestError
from .user_register_view import UserRegisterView

# Input data reused across the tests.
user_data = {"name": "Gabriel", "email": "gabriel@example.com", "password": "senha12345"}


# Fake controller: isolates the view from the real controller (no database, no password hashing).
# register is async in the real code, so we use AsyncMock; return_value mimics a successful response.
# The {**user_data} spreads the dict's keys inside attributes.
@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.register = AsyncMock(
        return_value={"type": "User", "count": 1, "attributes": {"id": 1, **user_data}}
    )
    return controller


# Happy path: registering responds 201 (Created) and calls the controller with the received body.
@pytest.mark.asyncio
async def test_user_register_view(mock_controller):
    http_request = HttpRequest(body=user_data)
    view = UserRegisterView(mock_controller)

    response = await view.handle(http_request)

    assert response.status_code == 201
    mock_controller.register.assert_awaited_once()
    # Confirms the view forwarded the body exactly as it received it.
    assert mock_controller.register.await_args.args[0] == user_data


# Error path: a domain error becomes a 400 HTTPException at the HTTP boundary.
@pytest.mark.asyncio
async def test_user_register_view_propagates_errors_as_http_exceptions(mock_controller):
    mock_controller.register = AsyncMock(side_effect=HttpBadRequestError("Email already registered"))
    view = UserRegisterView(mock_controller)
    http_request = HttpRequest(body=user_data)

    with pytest.raises(HTTPException) as e:
        await view.handle(http_request)

    assert e.value.status_code == 400
