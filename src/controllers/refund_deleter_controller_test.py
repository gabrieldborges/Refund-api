# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .refund_deleter_controller import RefundDeleterController


@pytest.fixture
def mock_repository():
    mock_repo = MagicMock()
    mock_repo.select_refund_by_id = AsyncMock(return_value={"id": 1, "user_id": 7, "filename": "abc.jpg"})
    mock_repo.delete_refund = AsyncMock()
    return mock_repo


@pytest.fixture
def mock_storage():
    mock_storage_instance = MagicMock()
    mock_storage_instance.delete = MagicMock()
    return mock_storage_instance


# Happy path: the owner deletes their own refund, and both the DB row and the
# receipt file on disk get cleaned up.
@pytest.mark.asyncio
async def test_owner_can_delete_their_own_refund_and_its_receipt_file(mock_repository, mock_storage):
    controller = RefundDeleterController(mock_repository, mock_storage)

    response = await controller.delete(refund_id=1, user_id=7, role="standard")

    mock_repository.delete_refund.assert_awaited_once_with(1)
    mock_storage.delete.assert_called_once_with("abc.jpg")
    assert response["attributes"]["deleted"] is True


@pytest.mark.asyncio
async def test_admin_can_delete_any_refund(mock_repository, mock_storage):
    controller = RefundDeleterController(mock_repository, mock_storage)

    await controller.delete(refund_id=1, user_id=999, role="admin")

    mock_repository.delete_refund.assert_awaited_once_with(1)


# Security: a standard user must not be able to delete someone else's refund — same
# "not found" response as a missing id, and nothing gets deleted (DB row or file).
@pytest.mark.asyncio
async def test_standard_user_cannot_delete_someone_elses_refund(mock_repository, mock_storage):
    controller = RefundDeleterController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.delete(refund_id=1, user_id=999, role="standard")

    mock_repository.delete_refund.assert_not_awaited()
    mock_storage.delete.assert_not_called()


@pytest.mark.asyncio
async def test_missing_refund_raises_not_found(mock_storage):
    mock_repo = MagicMock()
    mock_repo.select_refund_by_id = AsyncMock(return_value=None)
    controller = RefundDeleterController(mock_repo, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.delete(refund_id=999, user_id=7, role="standard")
