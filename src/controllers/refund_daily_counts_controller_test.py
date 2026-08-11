from datetime import date
from unittest.mock import AsyncMock
import pytest
from .refund_daily_counts_controller import RefundDailyCountsController


def _repo(counted=None):
    repo = AsyncMock()
    repo.count_by_day.return_value = counted or {}
    return repo


def _controller(repo):
    return RefundDailyCountsController(repo)


@pytest.mark.asyncio
async def test_every_day_of_the_month_is_present_with_zeros():
    response = await _controller(_repo()).count(user_id=1, role="admin", year=2026, month=8)

    assert len(response["days"]) == 31
    assert response["days"][0] == {"date": "2026-08-01", "count": 0}
    assert response["days"][-1] == {"date": "2026-08-31", "count": 0}


# The month length comes from the calendar module, not from a table of twelve
# numbers. February is where the difference shows.
@pytest.mark.asyncio
async def test_february_has_twenty_eight_days_in_a_common_year():
    response = await _controller(_repo()).count(user_id=1, role="admin", year=2026, month=2)

    assert len(response["days"]) == 28
    assert response["days"][-1]["date"] == "2026-02-28"


@pytest.mark.asyncio
async def test_february_has_twenty_nine_days_in_a_leap_year():
    response = await _controller(_repo()).count(user_id=1, role="admin", year=2024, month=2)

    assert len(response["days"]) == 29
    assert response["days"][-1]["date"] == "2024-02-29"


# 2100 is divisible by 4 but NOT a leap year — the century rule. Worth pinning
# because a hand-rolled `year % 4 == 0` would get it wrong and the endpoint accepts
# years up to 2100.
@pytest.mark.asyncio
async def test_the_century_rule_is_respected():
    response = await _controller(_repo()).count(user_id=1, role="admin", year=2100, month=2)

    assert len(response["days"]) == 28


@pytest.mark.asyncio
async def test_the_counted_days_are_merged_in():
    counted = {"2026-08-03": 2, "2026-08-09": 1}

    response = await _controller(_repo(counted)).count(
        user_id=1, role="admin", year=2026, month=8
    )

    by_date = {day["date"]: day["count"] for day in response["days"]}
    assert by_date["2026-08-03"] == 2
    assert by_date["2026-08-09"] == 1
    assert by_date["2026-08-04"] == 0


# A day the repository returned from outside the month must not appear: the series
# is driven by the calendar, not by the rows.
@pytest.mark.asyncio
async def test_a_day_outside_the_month_is_dropped():
    response = await _controller(_repo({"2026-07-31": 9})).count(
        user_id=1, role="admin", year=2026, month=8
    )

    assert all(day["date"].startswith("2026-08-") for day in response["days"])
    assert all(day["count"] == 0 for day in response["days"])


# Half-open window, and December has to roll the YEAR rather than produce month 13.
@pytest.mark.asyncio
async def test_the_window_is_the_month_half_open():
    repo = _repo()

    await _controller(repo).count(user_id=1, role="admin", year=2026, month=8)

    assert repo.count_by_day.await_args.kwargs["since"] == date(2026, 8, 1)
    assert repo.count_by_day.await_args.kwargs["until"] == date(2026, 9, 1)


@pytest.mark.asyncio
async def test_december_rolls_into_the_next_year():
    repo = _repo()

    await _controller(repo).count(user_id=1, role="admin", year=2026, month=12)

    assert repo.count_by_day.await_args.kwargs["until"] == date(2027, 1, 1)


@pytest.mark.asyncio
async def test_an_admin_without_a_filter_counts_everyone():
    repo = _repo()

    response = await _controller(repo).count(user_id=1, role="admin", year=2026, month=8)

    assert response["scope"] == "all"
    assert repo.count_by_day.await_args.kwargs["user_id"] is None


@pytest.mark.asyncio
async def test_an_admin_can_narrow_to_one_requester():
    repo = _repo()

    response = await _controller(repo).count(
        user_id=1, role="admin", year=2026, month=8, filter_user_id=7
    )

    assert response["scope"] == "user"
    assert repo.count_by_day.await_args.kwargs["user_id"] == 7


# Ignored, not rejected — the same choice refund_lister_controller makes.
@pytest.mark.asyncio
async def test_a_standard_user_only_ever_counts_themselves():
    repo = _repo()

    response = await _controller(repo).count(
        user_id=1, role="standard", year=2026, month=8, filter_user_id=7
    )

    assert response["scope"] == "user"
    assert repo.count_by_day.await_args.kwargs["user_id"] == 1


@pytest.mark.asyncio
async def test_the_response_names_its_type_and_month():
    response = await _controller(_repo()).count(user_id=1, role="admin", year=2026, month=8)

    assert response["type"] == "RefundDailyCounts"
    assert response["month"] == "2026-08"
