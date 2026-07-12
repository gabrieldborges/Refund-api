# pylint: disable=w0621
# w0621: the mock_controller parameter reuses the fixture's name (standard pytest pattern).
from unittest.mock import MagicMock, AsyncMock
import pytest
from fastapi import HTTPException
from src.views.http_types.http_request import HttpRequest
from src.errors.types.http_bad_request_error import HttpBadRequestError
from .user_login_view import UserLoginView

# Input data reused across the tests.
credentials = {"email": "gabriel@example.com", "password": "senha12345"}


# The view only orchestrates: receives the request, calls the controller, builds the HTTP
# response. Since we want to test the view in isolation (unit test), we swap the real
# controller for a mock. That way the test doesn't depend on database, password, JWT, etc.
# — only on the contract between view and controller.
@pytest.fixture
def mock_controller():
    controller = MagicMock()
    # login is async in the real code, so we use AsyncMock; return_value simulates the
    # response of a successful login.
    controller.login = AsyncMock(
        return_value={"access": True, "name": "Gabriel", "email": credentials["email"], "role": "standard", "token": "abc.def.ghi"}
    )
    return controller


# Happy path: the view must respond 200, pass through the controller's body, and have
# called the controller with the received body.
@pytest.mark.asyncio
async def test_user_login_view(mock_controller):
    http_request = HttpRequest(body=credentials)
    view = UserLoginView(mock_controller)

    response = await view.handle(http_request)

    assert response.status_code == 200
    assert response.body["access"] is True
    mock_controller.login.assert_awaited_once()
    # await_args.args[0] = the 1st positional argument login was called with.
    # Confirms the view forwarded exactly the request's body to the controller.
    assert mock_controller.login.await_args.args[0] == credentials


# Error path: if the controller raises a domain error (HttpBadRequestError), the view
# must convert it into a FastAPI HTTPException with the correct status code (400).
@pytest.mark.asyncio
async def test_user_login_view_propagates_errors_as_http_exceptions(mock_controller):
    # side_effect with an exception makes the mock raise that error when called.
    mock_controller.login = AsyncMock(side_effect=HttpBadRequestError("Invalid credentials"))
    view = UserLoginView(mock_controller)
    http_request = HttpRequest(body=credentials)

    with pytest.raises(HTTPException) as e:
        await view.handle(http_request)

    assert e.value.status_code == 400
