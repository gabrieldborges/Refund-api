# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .receipt_finder_controller import ReceiptFinderController


@pytest.fixture
def mock_repository():
    repository = MagicMock()
    repository.select_refund_by_id = AsyncMock(
        return_value={
            "id": 1, "name": "Almoço", "filename": "abc.jpg", "status": "pending",
            "user": {"id": 7, "name": "Gabriel", "avatar_filename": None},
        }
    )
    return repository


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.read = MagicMock(return_value=b"bytes do arquivo")
    return storage


@pytest.mark.asyncio
async def test_owner_receives_the_receipt(mock_repository, mock_storage):
    controller = ReceiptFinderController(mock_repository, mock_storage)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    mock_storage.read.assert_called_once_with("abc.jpg")
    assert response["content"] == b"bytes do arquivo"
    assert response["media_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_admin_receives_any_receipt(mock_repository, mock_storage):
    controller = ReceiptFinderController(mock_repository, mock_storage)

    response = await controller.find(refund_id=1, user_id=999, role="admin")

    assert response["content"] == b"bytes do arquivo"


# 404, never 403: a 403 would confirm the id is real and let an attacker
# enumerate refunds. Same rule as RefundFinderController (BR-013).
@pytest.mark.asyncio
async def test_someone_elses_receipt_is_not_found(mock_repository, mock_storage):
    controller = ReceiptFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError) as exception_info:
        await controller.find(refund_id=1, user_id=999, role="standard")

    # Pinning the literal message (not just the type) is what actually proves
    # this path is indistinguishable from the other two 404 paths below.
    assert exception_info.value.message == "Refund not found"
    mock_storage.read.assert_not_called()


@pytest.mark.asyncio
async def test_missing_refund_is_not_found(mock_repository, mock_storage):
    mock_repository.select_refund_by_id = AsyncMock(return_value=None)
    controller = ReceiptFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError) as exception_info:
        await controller.find(refund_id=999, user_id=7, role="standard")

    assert exception_info.value.message == "Refund not found"
    mock_storage.read.assert_not_called()


# The row survived but the file did not (the inverse of an orphaned file, which
# item 21 keeps possible). The same message keeps it indistinguishable from an
# unknown id.
@pytest.mark.asyncio
async def test_missing_file_on_disk_is_not_found(mock_repository, mock_storage):
    mock_storage.read = MagicMock(side_effect=FileNotFoundError())
    controller = ReceiptFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError) as exception_info:
        await controller.find(refund_id=1, user_id=7, role="standard")

    assert exception_info.value.message == "Refund not found"


@pytest.mark.asyncio
async def test_media_type_comes_from_the_stored_extension(mock_repository, mock_storage):
    mock_repository.select_refund_by_id = AsyncMock(
        return_value={"id": 1, "filename": "doc.pdf", "user": {"id": 7}}
    )
    controller = ReceiptFinderController(mock_repository, mock_storage)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    assert response["media_type"] == "application/pdf"
