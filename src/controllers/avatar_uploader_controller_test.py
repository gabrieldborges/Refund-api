# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .avatar_uploader_controller import AvatarUploaderController


@pytest.fixture
def mock_repository():
    repository = MagicMock()
    repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": None}
    )
    repository.update_avatar = AsyncMock()
    return repository


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.save = MagicMock(return_value="novo.jpg")
    storage.delete = MagicMock()
    return storage


@pytest.mark.asyncio
async def test_upload_saves_the_file_and_persists_its_name(mock_repository, mock_storage):
    controller = AvatarUploaderController(mock_repository, mock_storage)

    response = await controller.upload(user_id=7, original_filename="foto.jpg", content=b"x")

    mock_storage.save.assert_called_once_with("foto.jpg", b"x")
    mock_repository.update_avatar.assert_awaited_once_with(7, "novo.jpg")
    assert response["attributes"]["avatar_filename"] == "novo.jpg"


# Replacing the picture must remove the previous file, or every upload leaves one
# behind forever — which is exactly how this project accumulated orphaned files.
@pytest.mark.asyncio
async def test_replacing_the_picture_deletes_the_previous_file(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": "antiga.jpg"}
    )
    controller = AvatarUploaderController(mock_repository, mock_storage)

    await controller.upload(user_id=7, original_filename="foto.jpg", content=b"x")

    mock_storage.delete.assert_called_once_with("antiga.jpg")


# The first upload has nothing to delete; calling delete(None) would blow up.
@pytest.mark.asyncio
async def test_first_upload_deletes_nothing(mock_repository, mock_storage):
    controller = AvatarUploaderController(mock_repository, mock_storage)

    await controller.upload(user_id=7, original_filename="foto.jpg", content=b"x")

    mock_storage.delete.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_user_raises_not_found(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(return_value=None)
    controller = AvatarUploaderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.upload(user_id=999, original_filename="foto.jpg", content=b"x")

    mock_storage.save.assert_not_called()


# The order of these three calls is the whole point of the task: deleting the
# old file before the row points at the new one would leave the user with no
# picture at all if update_avatar failed, instead of merely leaking a file.
# Individual assert_called_once_with checks can't catch a reordering, so this
# pins the sequence via a shared call log across the three mocks.
@pytest.mark.asyncio
async def test_upload_saves_and_updates_before_deleting_the_previous_file(
    mock_repository, mock_storage
):
    mock_repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": "antiga.jpg"}
    )
    manager = MagicMock()
    manager.attach_mock(mock_storage.save, "save")
    manager.attach_mock(mock_repository.update_avatar, "update_avatar")
    manager.attach_mock(mock_storage.delete, "delete")
    controller = AvatarUploaderController(mock_repository, mock_storage)

    await controller.upload(user_id=7, original_filename="foto.jpg", content=b"x")

    call_order = [call[0] for call in manager.mock_calls]
    assert call_order == ["save", "update_avatar", "delete"]


# Item 21 — the new file is on disk before the column points at it. A failed
# update would leak it, exactly like the refund receipt case.
@pytest.mark.asyncio
async def test_upload_deletes_the_new_file_when_the_update_fails(
    mock_repository, mock_storage
):
    mock_repository.update_avatar = AsyncMock(side_effect=RuntimeError("database is down"))
    controller = AvatarUploaderController(mock_repository, mock_storage)

    with pytest.raises(RuntimeError):
        await controller.upload(user_id=7, original_filename="foto.jpg", content=b"x")

    mock_storage.delete.assert_called_once_with("novo.jpg")


# Replacing an existing avatar: once the column points at the new file, the
# upload has succeeded. Failing to remove the OLD one must not turn that into a
# 500 — the user's new picture is saved and live.
@pytest.mark.asyncio
async def test_upload_succeeds_even_when_removing_the_previous_file_fails(
    mock_repository, mock_storage
):
    mock_repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": "antiga.png"}
    )
    mock_storage.delete = MagicMock(side_effect=OSError("permission denied"))
    controller = AvatarUploaderController(mock_repository, mock_storage)

    response = await controller.upload(user_id=7, original_filename="foto.jpg", content=b"x")

    assert response["attributes"]["avatar_filename"] == "novo.jpg"
