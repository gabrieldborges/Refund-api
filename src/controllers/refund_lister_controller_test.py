# pylint: disable=w0621
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
from .refund_lister_controller import RefundListerController


@pytest.fixture
def mock_repository():
    mock_repo = MagicMock()
    # select_refunds now returns (rows, total, total_amount_in_cents), with each
    # row carrying the nested requester (real shape produced by Task 10's join).
    mock_repo.select_refunds = AsyncMock(
        return_value=(
            [
                {
                    "id": 1, "name": "Almoço", "category": "food", "amount_in_cents": 1000,
                    "filename": "a.jpg", "status": "pending", "created_at": None,
                    "user": {"id": 7, "name": "Ana", "avatar_filename": None},
                },
                {
                    "id": 2, "name": "Uber", "category": "transport", "amount_in_cents": 2000,
                    "filename": "b.jpg", "status": "approved", "created_at": None,
                    "user": {"id": 8, "name": "Bob", "avatar_filename": None},
                },
            ],
            2,
            19290,
        )
    )
    return mock_repo


# Security: a "standard" user must only ever see their own refunds, so the controller
# must pass their own user_id as the repository's filter.
@pytest.mark.asyncio
async def test_standard_user_lists_only_their_own_refunds(mock_repository):
    controller = RefundListerController(mock_repository)

    await controller.list(page=1, per_page=10, user_id=7, role="standard")

    mock_repository.select_refunds.assert_awaited_once_with(
        page=1, per_page=10, name=None, user_id=7,
        status=None, sort=None, order=None,
    )


# Security: an "admin" must see everyone's refunds, so the controller must pass
# user_id=None (no filter) to the repository, ignoring their own id.
@pytest.mark.asyncio
async def test_admin_lists_every_users_refunds(mock_repository):
    controller = RefundListerController(mock_repository)

    await controller.list(page=1, per_page=10, user_id=7, role="admin")

    mock_repository.select_refunds.assert_awaited_once_with(
        page=1, per_page=10, name=None, user_id=None,
        status=None, sort=None, order=None,
    )


@pytest.mark.asyncio
async def test_list_forwards_the_name_search_term(mock_repository):
    controller = RefundListerController(mock_repository)

    await controller.list(page=1, per_page=10, user_id=7, role="standard", name="Ana")

    mock_repository.select_refunds.assert_awaited_once_with(
        page=1, per_page=10, name="Ana", user_id=7,
        status=None, sort=None, order=None,
    )


# Pagination metadata (total_pages) must be computed from the repository's total count,
# not just from how many items came back on this page.
@pytest.mark.asyncio
async def test_response_includes_pagination_metadata(mock_repository):
    row = {
        "id": 1, "name": "Almoço", "category": "food", "amount_in_cents": 1000,
        "filename": "a.jpg", "status": "pending", "created_at": None,
        "user": {"id": 7, "name": "Ana", "avatar_filename": None},
    }
    mock_repository.select_refunds = AsyncMock(return_value=([row], 25, 50000))
    controller = RefundListerController(mock_repository)

    response = await controller.list(page=2, per_page=10, user_id=7, role="standard")

    assert response["count"] == 1
    assert response["total"] == 25
    assert response["page"] == 2
    assert response["per_page"] == 10
    assert response["total_pages"] == 3
    assert response["attributes"] == [
        {
            "id": 1, "name": "Almoço", "category": "food", "amount_in_cents": 1000,
            "status": "pending", "created_at": None,
            "user": {"id": 7, "name": "Ana", "has_avatar": False},
        }
    ]


# Edge case: zero results must not raise a division-by-zero when computing total_pages.
@pytest.mark.asyncio
async def test_response_with_zero_results_has_zero_total_pages(mock_repository):
    mock_repository.select_refunds = AsyncMock(return_value=([], 0, 0))
    controller = RefundListerController(mock_repository)

    response = await controller.list(page=1, per_page=10, user_id=7, role="standard")

    assert response["total_pages"] == 0


# Regression test: the repository returns created_at as a raw Python datetime (this is
# exactly what caused a 500 "Object of type datetime is not JSON serializable" in
# manual testing). The controller must convert it to an ISO string before it reaches
# the HTTP response.
@pytest.mark.asyncio
async def test_created_at_is_serialized_to_an_iso_string(mock_repository):
    raw_datetime = datetime(2026, 7, 12, 10, 30, 0)
    row = {
        "id": 1, "name": "Almoço", "category": "food", "amount_in_cents": 1000,
        "status": "pending", "created_at": raw_datetime,
        "user": {"id": 7, "name": "Ana", "avatar_filename": None},
    }
    mock_repository.select_refunds = AsyncMock(
        return_value=([row], 1, 1000)
    )
    controller = RefundListerController(mock_repository)

    response = await controller.list(page=1, per_page=10, user_id=7, role="standard")

    assert response["attributes"][0]["created_at"] == raw_datetime.isoformat()
    assert isinstance(response["attributes"][0]["created_at"], str)


# The summary band on the Home shows a total in cents for the whole filtered
# set, not just the current page, so the controller must forward the sum the
# repository computed instead of adding up the page it received.
@pytest.mark.asyncio
async def test_response_includes_the_total_amount(mock_repository):
    controller = RefundListerController(mock_repository)

    response = await controller.list(page=1, per_page=10, user_id=7, role="standard")

    assert response["sum_amount_in_cents"] == 19290


# Same guarantee as the detail response, for the list: every item carries status.
@pytest.mark.asyncio
async def test_list_items_include_the_status(mock_repository):
    row_1 = {
        "id": 1, "name": "Almoço", "category": "food", "amount_in_cents": 1000,
        "status": "pending", "created_at": None,
        "user": {"id": 7, "name": "Ana", "avatar_filename": None},
    }
    row_2 = {
        "id": 2, "name": "Uber", "category": "transport", "amount_in_cents": 2000,
        "status": "approved", "created_at": None,
        "user": {"id": 8, "name": "Bob", "avatar_filename": None},
    }
    mock_repository.select_refunds = AsyncMock(return_value=([row_1, row_2], 2, 19290))
    controller = RefundListerController(mock_repository)

    response = await controller.list(page=1, per_page=10, user_id=7, role="admin")

    assert [item["status"] for item in response["attributes"]] == ["pending", "approved"]


# The Home's filter bar and sortable columns rely on the controller forwarding
# status/sort/order straight through to the repository, alongside the existing filters.
@pytest.mark.asyncio
async def test_list_forwards_status_sort_and_order_to_the_repository(mock_repository):
    controller = RefundListerController(mock_repository)

    await controller.list(
        page=1, per_page=10, user_id=7, role="admin",
        status="pending", sort="amount_in_cents", order="asc",
    )

    mock_repository.select_refunds.assert_awaited_once_with(
        page=1, per_page=10, name=None, user_id=None,
        status="pending", sort="amount_in_cents", order="asc",
    )


# The repository already accepted user_id; only the controller decided it, and
# the route never exposed it. An admin can now scope the list to one requester.
@pytest.mark.asyncio
async def test_admin_can_filter_the_list_by_requester():
    repository = MagicMock()
    repository.select_refunds = AsyncMock(return_value=([], 0, 0))
    controller = RefundListerController(repository)

    await controller.list(page=1, per_page=10, user_id=9, role="admin", filter_user_id=3)

    assert repository.select_refunds.await_args.kwargs["user_id"] == 3


# A standard user is already locked to their own refunds, so the parameter is
# ignored rather than rejected: there is nothing to leak and no new error path.
@pytest.mark.asyncio
async def test_the_filter_is_ignored_for_a_standard_user():
    repository = MagicMock()
    repository.select_refunds = AsyncMock(return_value=([], 0, 0))
    controller = RefundListerController(repository)

    await controller.list(page=1, per_page=10, user_id=9, role="standard", filter_user_id=3)

    assert repository.select_refunds.await_args.kwargs["user_id"] == 9
