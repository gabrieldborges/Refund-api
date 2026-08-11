from unittest.mock import AsyncMock
import pytest
from src.errors.types.http_forbidden_error import HttpForbiddenError
from .user_lister_controller import UserListerController


def _repository(rows=None, total=0):
    repository = AsyncMock()
    repository.select_users.return_value = (rows or [], total)
    return repository


@pytest.mark.asyncio
async def test_an_admin_gets_the_serialized_list(user_row):
    controller = UserListerController(_repository([user_row()], total=1))

    response = await controller.list(page=1, per_page=10, role="admin")

    assert response["type"] == "User"
    assert response["total"] == 1
    assert response["attributes"][0]["name"] == "Ana"
    # Goes through serialize_user rather than handing the repository row over.
    assert "password" not in response["attributes"][0]


@pytest.mark.asyncio
async def test_a_standard_user_is_forbidden():
    with pytest.raises(HttpForbiddenError):
        await UserListerController(_repository()).list(page=1, per_page=10, role="standard")


# The important half of the rule. Refusing AFTER querying would run work for a
# request that was never allowed, and the response time would still tell an
# outsider roughly how many users exist. Same idiom as
# refund_reviewer_controller.py:30.
@pytest.mark.asyncio
async def test_the_repository_is_never_reached_for_a_standard_user():
    repository = _repository()

    with pytest.raises(HttpForbiddenError):
        await UserListerController(repository).list(page=1, per_page=10, role="standard")

    repository.select_users.assert_not_called()


@pytest.mark.asyncio
async def test_the_pagination_and_name_filter_reach_the_repository():
    repository = _repository()

    await UserListerController(repository).list(page=2, per_page=5, role="admin", name="an")

    repository.select_users.assert_awaited_once_with(page=2, per_page=5, name="an")


# The envelope's page metadata has to echo the request, not the repository's
# row count: a page beyond the end is empty but still page N.
@pytest.mark.asyncio
async def test_the_envelope_echoes_the_requested_page():
    response = await UserListerController(_repository([], total=25)).list(
        page=3, per_page=10, role="admin"
    )

    assert response["page"] == 3
    assert response["per_page"] == 10
    assert response["total"] == 25
    assert response["total_pages"] == 3
    assert response["count"] == 0
