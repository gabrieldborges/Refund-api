# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.views.http_types.http_request import HttpRequest
from .avatar_remover_view import AvatarRemoverView


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.remove = AsyncMock(
        return_value={"type": "User", "count": 1, "attributes": {"avatar_filename": None}}
    )
    return controller


@pytest.mark.asyncio
async def test_remove_reaches_the_controller_with_the_token_user(mock_controller):
    view = AvatarRemoverView(mock_controller)
    http_request = HttpRequest(token_info={"user_id": 7, "role": "standard"})

    http_response = await view.handle(http_request)

    mock_controller.remove.assert_awaited_once_with(user_id=7)
    assert http_response.status_code == 200
