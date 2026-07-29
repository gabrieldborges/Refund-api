# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .avatar_finder_controller import AvatarFinderController


@pytest.fixture
def mock_repository():
    repository = MagicMock()
    repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": "foto.png"}
    )
    return repository


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.read = MagicMock(return_value=b"bytes da foto")
    return storage


# Any authenticated user may fetch any avatar, so the controller takes no
# identity of its own: it is not an authorization decision, only a lookup.
@pytest.mark.asyncio
async def test_any_users_avatar_can_be_fetched(mock_repository, mock_storage):
    controller = AvatarFinderController(mock_repository, mock_storage)

    response = await controller.find(user_id=7)

    mock_storage.read.assert_called_once_with("foto.png")
    assert response["content"] == b"bytes da foto"
    assert response["media_type"] == "image/png"


@pytest.mark.asyncio
async def test_user_without_a_picture_is_not_found(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": None}
    )
    controller = AvatarFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.find(user_id=7)

    mock_storage.read.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_user_is_not_found(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(return_value=None)
    controller = AvatarFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.find(user_id=999)

    mock_storage.read.assert_not_called()


@pytest.mark.asyncio
async def test_missing_file_on_disk_is_not_found(mock_repository, mock_storage):
    mock_storage.read = MagicMock(side_effect=FileNotFoundError())
    controller = AvatarFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.find(user_id=7)
