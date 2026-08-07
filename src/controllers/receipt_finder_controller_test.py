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
    storage.get_url = MagicMock(return_value="https://signed.example/file?token=t")
    return storage


@pytest.mark.asyncio
async def test_owner_receives_the_receipt(mock_repository, mock_storage):
    controller = ReceiptFinderController(mock_repository, mock_storage)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    mock_storage.get_url.assert_called_once_with("abc.jpg")
    assert response["url"] == "https://signed.example/file?token=t"


@pytest.mark.asyncio
async def test_admin_receives_any_receipt(mock_repository, mock_storage):
    controller = ReceiptFinderController(mock_repository, mock_storage)

    response = await controller.find(refund_id=1, user_id=999, role="admin")

    assert response["url"] == "https://signed.example/file?token=t"


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
    mock_storage.get_url.assert_not_called()


@pytest.mark.asyncio
async def test_missing_refund_is_not_found(mock_repository, mock_storage):
    mock_repository.select_refund_by_id = AsyncMock(return_value=None)
    controller = ReceiptFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError) as exception_info:
        await controller.find(refund_id=999, user_id=7, role="standard")

    assert exception_info.value.message == "Refund not found"
    mock_storage.get_url.assert_not_called()


# BEHAVIOUR REMOVED BY ITEM 22, recorded rather than deleted quietly. This used
# to assert that "the row survived but the file did not" answered 404 here,
# because the controller read the bytes. It mints a signed URL now and never
# touches storage, so that case surfaces when the browser follows the URL —
# /files answers 404 locally, the bucket does with S3.
#
# What replaced it is the assertion below: a URL is produced from the stored
# filename without any existence check. Restoring the old behaviour would cost
# a HEAD request per URL against S3, which is most of what this item avoids.
@pytest.mark.asyncio
async def test_a_url_is_minted_without_checking_that_the_file_exists(
    mock_repository, mock_storage
):
    controller = ReceiptFinderController(mock_repository, mock_storage)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    mock_storage.get_url.assert_called_once_with("abc.jpg")
    assert response["url"] == "https://signed.example/file?token=t"


# ALSO MOVED BY ITEM 22. media_type used to be derived here, because this
# controller produced the bytes. The response carries only a URL now, and the
# content type is decided where the bytes are actually served: the /files route
# for local storage (see file_routes_test.py), the bucket's stored metadata for
# S3. Deriving it from the stored extension rather than a client header is the
# rule that survived the move.
@pytest.mark.asyncio
async def test_the_url_is_built_from_the_stored_filename(mock_repository, mock_storage):
    mock_repository.select_refund_by_id = AsyncMock(
        return_value={"id": 1, "filename": "doc.pdf", "user": {"id": 7}}
    )
    controller = ReceiptFinderController(mock_repository, mock_storage)

    await controller.find(refund_id=1, user_id=7, role="standard")

    mock_storage.get_url.assert_called_once_with("doc.pdf")


# The client has to choose between <img> and <object> BEFORE fetching, and a
# URL carries no type — so media_type stays in the response even though the
# bytes now come from somewhere else.
@pytest.mark.asyncio
async def test_the_response_carries_the_media_type(mock_repository, mock_storage):
    controller = ReceiptFinderController(mock_repository, mock_storage)

    response = await controller.find(refund_id=1, user_id=7, role="standard")

    assert response["media_type"] == "image/jpeg"
