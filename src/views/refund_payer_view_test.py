from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException
from src.views.http_types.http_request import HttpRequest
from .refund_payer_view import RefundPayerView


# The validator runs before the controller: an invalid file must short-circuit
# with a 422 and never reach the transaction. The view catches the domain error
# and error_handler converts it, so what surfaces here is HTTPException — the
# same pattern asserted in refund_reviewer_view_test.py.
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

    with pytest.raises(HTTPException) as exception_info:
        await view.handle(request)

    assert exception_info.value.status_code == 422
    controller.pay.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_valid_upload_reaches_the_controller():
    controller = MagicMock()
    controller_response = {"type": "Refund", "count": 1, "attributes": {}}
    controller.pay = AsyncMock(return_value=controller_response)
    view = RefundPayerView(controller)
    request = HttpRequest(
        body={"filename": "proof.pdf", "content": b"x"},
        path_params={"refund_id": 1},
        token_info={"user_id": 9, "role": "admin"},
    )

    response = await view.handle(request)

    assert response.status_code == 200
    assert response.body == controller_response
    controller.pay.assert_awaited_once_with(
        refund_id=1, payer_id=9, role="admin", filename="proof.pdf", content=b"x"
    )
