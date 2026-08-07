# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .avatar_remover_controller import AvatarRemoverController


@pytest.fixture
def mock_repository():
    repository = MagicMock()
    repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": "atual.jpg"}
    )
    repository.update_avatar = AsyncMock()
    return repository


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.delete = MagicMock()
    return storage


@pytest.mark.asyncio
async def test_remove_clears_the_column_and_deletes_the_file(mock_repository, mock_storage):
    controller = AvatarRemoverController(mock_repository, mock_storage)

    response = await controller.remove(user_id=7)

    mock_repository.update_avatar.assert_awaited_once_with(7, None)
    mock_storage.delete.assert_called_once_with("atual.jpg")
    assert response["attributes"]["avatar_filename"] is None


# Removing when there is no picture is a no-op that still succeeds: the caller
# asked for "no avatar" and that is the resulting state.
@pytest.mark.asyncio
async def test_remove_is_idempotent_when_there_is_no_picture(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": None}
    )
    controller = AvatarRemoverController(mock_repository, mock_storage)

    response = await controller.remove(user_id=7)

    mock_storage.delete.assert_not_called()
    assert response["attributes"]["avatar_filename"] is None


@pytest.mark.asyncio
async def test_unknown_user_raises_not_found(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(return_value=None)
    controller = AvatarRemoverController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.remove(user_id=999)


# Same ordering guarantee as the uploader: clearing the column before deleting
# the file means a crash mid-operation leaves a leaked file at worst, never a
# row pointing at a file that no longer exists. Pin the sequence via a shared
# call log, since separate assert_called_once_with checks don't see order.
@pytest.mark.asyncio
async def test_remove_updates_before_deleting_the_file(mock_repository, mock_storage):
    manager = MagicMock()
    manager.attach_mock(mock_repository.update_avatar, "update_avatar")
    manager.attach_mock(mock_storage.delete, "delete")
    controller = AvatarRemoverController(mock_repository, mock_storage)

    await controller.remove(user_id=7)

    call_order = [call[0] for call in manager.mock_calls]
    assert call_order == ["update_avatar", "delete"]


# Item 21 — the column is cleared and committed before the file is removed. As
# far as the product is concerned the avatar is already gone, so a failure to
# delete the file must not answer 500 to a removal that worked.
@pytest.mark.asyncio
async def test_remove_succeeds_even_when_deleting_the_file_fails(
    mock_repository, mock_storage
):
    mock_storage.delete = MagicMock(side_effect=OSError("permission denied"))
    controller = AvatarRemoverController(mock_repository, mock_storage)

    response = await controller.remove(user_id=7)

    assert response["attributes"]["avatar_filename"] is None
