# pylint: disable=w0621
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.errors.types.http_not_found_error import HttpNotFoundError
from .refund_stats_finder_controller import RefundStatsFinderController


def build_controller(totals):
    repository = MagicMock()
    repository.count_by_status = AsyncMock(return_value=totals)
    return RefundStatsFinderController(repository)


# Every status is present even when the user has none of it. Dropping empty
# keys would force every client to handle a missing key.
@pytest.mark.asyncio
async def test_statuses_with_no_refunds_come_back_as_zeros():
    controller = build_controller({"approved": {"count": 2, "amount_in_cents": 5000}})

    response = await controller.find(target_user_id=3, user_id=3, role="standard")

    assert response["by_status"] == {
        "pending": {"count": 0, "amount_in_cents": 0},
        "approved": {"count": 2, "amount_in_cents": 5000},
        "paid": {"count": 0, "amount_in_cents": 0},
        "rejected": {"count": 0, "amount_in_cents": 0},
    }
    assert response["user_id"] == 3


# There is no total, of count or of amount: summing across statuses would add a
# forecast to a liability to a realised expense. Clients derive what they need.
@pytest.mark.asyncio
async def test_the_response_publishes_no_cross_status_total():
    controller = build_controller({})

    response = await controller.find(target_user_id=3, user_id=3, role="standard")

    assert "total" not in response
    assert set(response.keys()) == {"type", "user_id", "by_status"}


@pytest.mark.asyncio
async def test_admin_reads_someone_elses_stats():
    controller = build_controller({})

    response = await controller.find(target_user_id=3, user_id=99, role="admin")

    assert response["user_id"] == 3


# 404 rather than 403, for the same anti-enumeration reason as BR-013: a 403
# would confirm that user id exists.
@pytest.mark.asyncio
async def test_a_standard_user_cannot_read_someone_elses_stats():
    controller = build_controller({})

    with pytest.raises(HttpNotFoundError):
        await controller.find(target_user_id=3, user_id=7, role="standard")
