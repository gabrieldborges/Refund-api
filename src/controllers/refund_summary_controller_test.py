from datetime import datetime
from unittest.mock import AsyncMock
import pytest
from .refund_summary_controller import RefundSummaryController

NOW = datetime(2026, 8, 11, 12, 0, 0)


def _repo(by_status=None, by_category=None, by_month=None):
    repo = AsyncMock()
    repo.summarize_refunds.return_value = (by_status or {}, by_category or {}, by_month or [])
    return repo


def _controller(repo):
    # The clock is INJECTED rather than patched: a test that froze datetime
    # globally would freeze it for everything else in the same process, and a
    # controller calling datetime.now() directly would make these window
    # assertions start failing by themselves at the turn of a month.
    return RefundSummaryController(repo, clock=lambda: NOW)


# The four statuses and five categories are always present, zeros included — the
# contract UC-014 established, for the same reason: an absent key makes the client
# branch on undefined, and "zero" is not "does not exist".
@pytest.mark.asyncio
async def test_every_status_and_category_key_is_present_with_zeros():
    response = await _controller(_repo()).summarize(user_id=1, role="admin", months=6)

    assert set(response["by_status"]) == {"pending", "approved", "paid", "rejected"}
    assert set(response["by_category"]) == {
        "food",
        "lodging",
        "transport",
        "service",
        "others",
    }
    assert response["by_status"]["paid"] == {"count": 0, "amount_in_cents": 0}
    assert response["by_category"]["food"] == {"count": 0, "amount_in_cents": 0}


# Every month in the window, oldest first, including the empty ones: a gap in the
# series would make the line chart lie about its slope.
@pytest.mark.asyncio
async def test_every_month_in_the_window_is_present_in_order():
    response = await _controller(_repo()).summarize(user_id=1, role="admin", months=6)

    assert [month["month"] for month in response["by_month"]] == [
        "2026-03",
        "2026-04",
        "2026-05",
        "2026-06",
        "2026-07",
        "2026-08",
    ]


# The window has to cross a year boundary correctly, which is the arithmetic most
# likely to be written wrong.
@pytest.mark.asyncio
async def test_the_window_crosses_the_year_boundary():
    response = await _controller(_repo()).summarize(user_id=1, role="admin", months=10)

    assert response["by_month"][0]["month"] == "2025-11"
    assert response["by_month"][1]["month"] == "2025-12"
    assert response["by_month"][2]["month"] == "2026-01"


@pytest.mark.asyncio
async def test_an_empty_month_is_zero_rather_than_absent():
    rows = [{"month": "2026-08", "status": "paid", "count": 2, "amount_in_cents": 5000}]

    response = await _controller(_repo(by_month=rows)).summarize(
        user_id=1, role="admin", months=6
    )

    march = response["by_month"][0]
    assert march["month"] == "2026-03"
    assert march["count"] == 0
    assert march["by_status"]["paid"] == {"count": 0, "amount_in_cents": 0}


# The month's own totals are summed here, so the client never adds them up and
# never disagrees with the server about them.
@pytest.mark.asyncio
async def test_a_month_total_is_the_sum_of_its_statuses():
    rows = [
        {"month": "2026-08", "status": "paid", "count": 2, "amount_in_cents": 5000},
        {"month": "2026-08", "status": "pending", "count": 1, "amount_in_cents": 1500},
    ]

    response = await _controller(_repo(by_month=rows)).summarize(
        user_id=1, role="admin", months=6
    )

    august = response["by_month"][-1]
    assert august["count"] == 3
    assert august["amount_in_cents"] == 6500


# A month outside the window must not appear even if the repository returned it.
@pytest.mark.asyncio
async def test_a_month_outside_the_window_is_dropped():
    rows = [{"month": "2025-01", "status": "paid", "count": 9, "amount_in_cents": 9000}]

    response = await _controller(_repo(by_month=rows)).summarize(
        user_id=1, role="admin", months=6
    )

    assert [month["month"] for month in response["by_month"]][0] == "2026-03"
    assert all(month["count"] == 0 for month in response["by_month"])


@pytest.mark.asyncio
async def test_an_admin_without_a_filter_aggregates_everyone():
    repo = _repo()

    response = await _controller(repo).summarize(user_id=1, role="admin", months=6)

    assert response["scope"] == "all"
    assert repo.summarize_refunds.await_args.kwargs["user_id"] is None


@pytest.mark.asyncio
async def test_an_admin_can_narrow_to_one_requester():
    repo = _repo()

    response = await _controller(repo).summarize(
        user_id=1, role="admin", months=6, filter_user_id=7
    )

    assert response["scope"] == "user"
    assert repo.summarize_refunds.await_args.kwargs["user_id"] == 7


# The rule that matters: a standard user's filter_user_id is IGNORED, not
# rejected. They are already locked to themselves, so there is nothing to leak and
# no new error path to document — the same choice refund_lister_controller makes.
@pytest.mark.asyncio
async def test_a_standard_user_only_ever_aggregates_themselves():
    repo = _repo()

    response = await _controller(repo).summarize(
        user_id=1, role="standard", months=6, filter_user_id=7
    )

    assert response["scope"] == "user"
    assert repo.summarize_refunds.await_args.kwargs["user_id"] == 1


# Truncated to the first day of the oldest month, not "N times 30 days ago": a
# partial oldest month would render as a short bar beside full ones and read as a
# drop that never happened.
@pytest.mark.asyncio
async def test_the_window_starts_at_the_first_day_of_the_oldest_month():
    repo = _repo()

    await _controller(repo).summarize(user_id=1, role="admin", months=6)

    assert repo.summarize_refunds.await_args.kwargs["since"] == datetime(2026, 3, 1)


@pytest.mark.asyncio
async def test_the_response_echoes_the_window_and_names_its_type():
    response = await _controller(_repo()).summarize(user_id=1, role="admin", months=3)

    assert response["type"] == "RefundSummary"
    assert response["months"] == 3
    assert len(response["by_month"]) == 3


# A single month is the smallest legal window, and the arithmetic must not produce
# an empty list for it.
@pytest.mark.asyncio
async def test_a_single_month_window_returns_that_month():
    response = await _controller(_repo()).summarize(user_id=1, role="admin", months=1)

    assert [month["month"] for month in response["by_month"]] == ["2026-08"]
