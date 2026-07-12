# pylint: disable=w0621
from unittest.mock import MagicMock, AsyncMock
import pytest
from fastapi import HTTPException
from src.views.http_types.http_request import HttpRequest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .refund_deleter_view import RefundDeleterView


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.delete = AsyncMock(
        return_value={"type": "Refund", "count": 1, "attributes": {"id": 1, "deleted": True}}
    )
    return controller


@pytest.mark.asyncio
async def test_refund_deleter_view_forwards_refund_id_and_token_info(mock_controller):
    http_request = HttpRequest(
        path_params={"refund_id": 1}, token_info={"user_id": 7, "role": "standard"}
    )
    view = RefundDeleterView(mock_controller)

    response = await view.handle(http_request)

    assert response.status_code == 200
    mock_controller.delete.assert_awaited_once_with(1, 7, "standard")


@pytest.mark.asyncio
async def test_refund_deleter_view_converts_not_found_into_http_exception(mock_controller):
    mock_controller.delete = AsyncMock(side_effect=HttpNotFoundError("Refund not found"))
    http_request = HttpRequest(
        path_params={"refund_id": 999}, token_info={"user_id": 7, "role": "standard"}
    )
    view = RefundDeleterView(mock_controller)

    with pytest.raises(HTTPException) as e:
        await view.handle(http_request)

    assert e.value.status_code == 404
