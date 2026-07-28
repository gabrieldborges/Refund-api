# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException
from src.views.http_types.http_request import HttpRequest
from .refund_reviewer_view import RefundReviewerView


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.review = AsyncMock(
        return_value={"type": "Refund", "count": 1, "attributes": {"id": 1, "status": "approved"}}
    )
    return controller


@pytest.mark.asyncio
async def test_valid_request_reaches_the_controller_and_returns_200(mock_controller):
    view = RefundReviewerView(mock_controller)
    http_request = HttpRequest(
        path_params={"refund_id": 1},
        body={"status": "approved", "reason": None},
        token_info={"user_id": 9, "role": "admin"},
    )

    http_response = await view.handle(http_request)

    mock_controller.review.assert_awaited_once_with(
        refund_id=1, reviewer_id=9, role="admin", status="approved", reason=None
    )
    assert http_response.status_code == 200


# The validator runs before the controller: an invalid body must short-circuit
# with a 422 and never reach the transaction. The view catches the domain error
# and error_handler converts it, so what surfaces here is HTTPException — the
# same pattern asserted in refund_creator_view_test.py.
@pytest.mark.asyncio
async def test_invalid_status_short_circuits_before_the_controller(mock_controller):
    view = RefundReviewerView(mock_controller)
    http_request = HttpRequest(
        path_params={"refund_id": 1},
        body={"status": "whatever", "reason": None},
        token_info={"user_id": 9, "role": "admin"},
    )

    with pytest.raises(HTTPException) as exception_info:
        await view.handle(http_request)

    assert exception_info.value.status_code == 422
    mock_controller.review.assert_not_awaited()
