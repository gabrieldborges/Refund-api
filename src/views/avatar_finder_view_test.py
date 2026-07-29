# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.views.http_types.http_request import HttpRequest
from .avatar_finder_view import AvatarFinderView


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.find = AsyncMock(return_value={"content": b"x", "media_type": "image/png"})
    return controller


# The user id comes from the path, not the token: this endpoint serves any
# user's avatar to any authenticated caller.
@pytest.mark.asyncio
async def test_the_view_uses_the_path_user_id(mock_controller):
    view = AvatarFinderView(mock_controller)
    http_request = HttpRequest(
        path_params={"user_id": 13},
        token_info={"user_id": 7, "role": "standard"},
    )

    http_response = await view.handle(http_request)

    mock_controller.find.assert_awaited_once_with(user_id=13)
    assert http_response.status_code == 200
