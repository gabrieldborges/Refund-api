# pylint: disable=w0621
from unittest.mock import MagicMock, AsyncMock
import pytest
from src.views.http_types.http_request import HttpRequest
from .refund_lister_view import RefundListerView


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.list = AsyncMock(
        return_value={"type": "Refund", "count": 0, "total": 0, "page": 1, "per_page": 10, "total_pages": 0, "attributes": []}
    )
    return controller


# Happy path: query params + token info are correctly unpacked and forwarded to the controller.
@pytest.mark.asyncio
async def test_refund_lister_view_forwards_query_and_token_info_to_the_controller(mock_controller):
    http_request = HttpRequest(
        query={"page": 2, "per_page": 20, "name": "Ana"},
        token_info={"user_id": 7, "role": "standard"},
    )
    view = RefundListerView(mock_controller)

    response = await view.handle(http_request)

    assert response.status_code == 200
    mock_controller.list.assert_awaited_once_with(
        page=2, per_page=20, name="Ana", user_id=7, role="standard"
    )


# When "name" is absent from the query dict, the view must pass None, not raise a KeyError.
@pytest.mark.asyncio
async def test_refund_lister_view_defaults_name_to_none_when_absent(mock_controller):
    http_request = HttpRequest(
        query={"page": 1, "per_page": 10},
        token_info={"user_id": 7, "role": "admin"},
    )
    view = RefundListerView(mock_controller)

    await view.handle(http_request)

    mock_controller.list.assert_awaited_once_with(
        page=1, per_page=10, name=None, user_id=7, role="admin"
    )
