from unittest.mock import AsyncMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .user_finder_controller import UserFinderController


def _repository(user=None):
    repository = AsyncMock()
    repository.select_user_by_id.return_value = user
    return repository


@pytest.mark.asyncio
async def test_an_admin_gets_the_serialized_user(user_row):
    response = await UserFinderController(_repository(user_row())).find(user_id=7, role="admin")

    assert response["type"] == "User"
    assert response["count"] == 1
    assert response["attributes"]["name"] == "Ana"
    assert "password" not in response["attributes"]


# 404 and not 403: a 403 would confirm that user 7 exists to somebody who is not
# allowed to know. This test and the next one must be indistinguishable from the
# caller's side — that is the whole point of the choice.
@pytest.mark.asyncio
async def test_a_standard_user_gets_not_found(user_row):
    with pytest.raises(HttpNotFoundError) as error:
        await UserFinderController(_repository(user_row())).find(user_id=7, role="standard")

    assert str(error.value) == "User not found"


@pytest.mark.asyncio
async def test_a_missing_user_gets_not_found():
    with pytest.raises(HttpNotFoundError) as error:
        await UserFinderController(_repository(None)).find(user_id=999, role="admin")

    # Byte-identical to the message above, so the two cases cannot be told apart.
    assert str(error.value) == "User not found"


@pytest.mark.asyncio
async def test_the_repository_is_never_reached_for_a_standard_user(user_row):
    repository = _repository(user_row())

    with pytest.raises(HttpNotFoundError):
        await UserFinderController(repository).find(user_id=7, role="standard")

    repository.select_user_by_id.assert_not_called()
