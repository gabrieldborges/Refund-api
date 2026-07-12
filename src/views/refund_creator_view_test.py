# pylint: disable=w0621
from unittest.mock import MagicMock, AsyncMock
import pytest
from fastapi import HTTPException
from src.views.http_types.http_request import HttpRequest
from .refund_creator_view import RefundCreatorView


def valid_body(**overrides):
    body = {
        "name": "Ana Silva", "category": "food", "amount": 45.90,
        "filename": "receipt.jpg", "content_type": "image/jpeg", "content": b"x" * 100,
    }
    body.update(overrides)
    return body


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.create = AsyncMock(
        return_value={"type": "Refund", "count": 1, "attributes": {"id": 1}}
    )
    return controller


# Happy path: valid body + a logged-in user -> 201, and the controller receives the
# request body plus the user_id extracted from the token (not from the client's body).
@pytest.mark.asyncio
async def test_refund_creator_view_happy_path(mock_controller):
    body = valid_body()
    http_request = HttpRequest(body=body, token_info={"user_id": 7, "role": "standard"})
    view = RefundCreatorView(mock_controller)

    response = await view.handle(http_request)

    assert response.status_code == 201
    mock_controller.create.assert_awaited_once()
    assert mock_controller.create.await_args.args == (body, 7)


# The validator runs before the controller: an invalid category must short-circuit
# with a 422 and the controller must never even be called.
@pytest.mark.asyncio
async def test_refund_creator_view_rejects_invalid_category_before_calling_controller(mock_controller):
    http_request = HttpRequest(
        body=valid_body(category="vacation"), token_info={"user_id": 7, "role": "standard"}
    )
    view = RefundCreatorView(mock_controller)

    with pytest.raises(HTTPException) as e:
        await view.handle(http_request)

    assert e.value.status_code == 422
    mock_controller.create.assert_not_awaited()
