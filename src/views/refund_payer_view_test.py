from unittest.mock import AsyncMock, MagicMock
import pytest
from src.views.http_types.http_request import HttpRequest
from .refund_payer_view import RefundPayerView


# The validator runs BEFORE the controller, so a malformed upload never reaches
# the database — the same short-circuit RefundReviewerView relies on.
@pytest.mark.asyncio
async def test_invalid_file_short_circuits_before_the_controller():
    controller = MagicMock()
    controller.pay = AsyncMock()
    view = RefundPayerView(controller)
    request = HttpRequest(
        body={"filename": "proof.exe", "content": b"x"},
        path_params={"refund_id": 1},
        token_info={"user_id": 9, "role": "admin"},
    )

    with pytest.raises(Exception):
        await view.handle(request)

    controller.pay.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_valid_upload_reaches_the_controller():
    controller = MagicMock()
    controller.pay = AsyncMock(return_value={"type": "Refund", "count": 1, "attributes": {}})
    view = RefundPayerView(controller)
    request = HttpRequest(
        body={"filename": "proof.pdf", "content": b"x"},
        path_params={"refund_id": 1},
        token_info={"user_id": 9, "role": "admin"},
    )

    response = await view.handle(request)

    assert response.status_code == 200
    controller.pay.assert_awaited_once_with(
        refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
    )
