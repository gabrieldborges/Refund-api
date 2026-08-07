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
    storage.get_url = MagicMock(return_value="https://signed.example/file?token=t")
    return storage


# Any authenticated user may fetch any avatar, so the controller takes no
# identity of its own: it is not an authorization decision, only a lookup.
@pytest.mark.asyncio
async def test_any_users_avatar_can_be_fetched(mock_repository, mock_storage):
    controller = AvatarFinderController(mock_repository, mock_storage)

    response = await controller.find(user_id=7)

    mock_storage.get_url.assert_called_once_with("foto.png")
    assert response["url"] == "https://signed.example/file?token=t"


@pytest.mark.asyncio
async def test_user_without_a_picture_is_not_found(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(
        return_value={"id": 7, "name": "Gabriel", "avatar_filename": None}
    )
    controller = AvatarFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.find(user_id=7)

    mock_storage.get_url.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_user_is_not_found(mock_repository, mock_storage):
    mock_repository.select_user_by_id = AsyncMock(return_value=None)
    controller = AvatarFinderController(mock_repository, mock_storage)

    with pytest.raises(HttpNotFoundError):
        await controller.find(user_id=999)

    mock_storage.get_url.assert_not_called()


# BEHAVIOUR REMOVED BY ITEM 22 — see the note in
# receipt_finder_controller_test.py. The controller no longer reads the file,
# so a missing one is discovered when the URL is followed, not here.
@pytest.mark.asyncio
async def test_a_url_is_minted_without_checking_that_the_file_exists(
    mock_repository, mock_storage
):
    controller = AvatarFinderController(mock_repository, mock_storage)

    response = await controller.find(user_id=7)

    assert response["url"] == "https://signed.example/file?token=t"


@pytest.mark.asyncio
async def test_the_response_carries_the_media_type(mock_repository, mock_storage):
    controller = AvatarFinderController(mock_repository, mock_storage)

    response = await controller.find(user_id=7)

    assert response["media_type"] == "image/png"
