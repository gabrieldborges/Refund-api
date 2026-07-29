# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi import HTTPException
from src.views.http_types.http_request import HttpRequest
from .avatar_uploader_view import AvatarUploaderView


@pytest.fixture
def mock_controller():
    controller = MagicMock()
    controller.upload = AsyncMock(
        return_value={"type": "User", "count": 1, "attributes": {"avatar_filename": "a.jpg"}}
    )
    return controller


@pytest.mark.asyncio
async def test_valid_upload_reaches_the_controller(mock_controller):
    view = AvatarUploaderView(mock_controller)
    http_request = HttpRequest(
        body={"filename": "foto.jpg", "content": b"x"},
        token_info={"user_id": 7, "role": "standard"},
    )

    http_response = await view.handle(http_request)

    mock_controller.upload.assert_awaited_once_with(
        user_id=7, original_filename="foto.jpg", content=b"x"
    )
    assert http_response.status_code == 200


# The validator runs before the controller: a PDF must be refused with 422 and
# must never reach the disk.
@pytest.mark.asyncio
async def test_pdf_is_refused_before_the_controller(mock_controller):
    view = AvatarUploaderView(mock_controller)
    http_request = HttpRequest(
        body={"filename": "foto.pdf", "content": b"x"},
        token_info={"user_id": 7, "role": "standard"},
    )

    with pytest.raises(HTTPException) as exception_info:
        await view.handle(http_request)

    assert exception_info.value.status_code == 422
    mock_controller.upload.assert_not_awaited()
