# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.views.http_types.http_request import HttpRequest
from .receipt_finder_view import ReceiptFinderView


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.find = AsyncMock(return_value={"content": b"x", "media_type": "image/jpeg"})
    return controller


@pytest.mark.asyncio
async def test_the_view_passes_the_token_identity_to_the_controller(mock_controller):
    view = ReceiptFinderView(mock_controller)
    http_request = HttpRequest(
        path_params={"refund_id": 1},
        token_info={"user_id": 7, "role": "standard"},
    )

    http_response = await view.handle(http_request)

    mock_controller.find.assert_awaited_once_with(refund_id=1, user_id=7, role="standard")
    assert http_response.status_code == 200
    assert http_response.body["content"] == b"x"
