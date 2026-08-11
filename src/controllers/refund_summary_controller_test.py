from datetime import datetime
from unittest.mock import AsyncMock
import pytest
from .refund_summary_controller import RefundSummaryController

NOW = datetime(2026, 8, 11, 12, 0, 0)


def _repo(by_status=None, by_category=None, by_month=None, years=None):
    repo = AsyncMock()
    repo.summarize_refunds.return_value = (by_status or {}, by_category or {}, by_month or [])
    repo.available_years.return_value = years if years is not None else [2025, 2026]
    return repo


def _controller(repo):
    # The clock is INJECTED rather than patched: a test that froze datetime
    # globally would freeze it for everything else in the same process, and a
    # controller calling datetime.now() directly would make the default-year
    # assertion start failing by itself at the turn of a year.
    return RefundSummaryController(repo, clock=lambda: NOW)


# The four statuses and five categories are always present, zeros included — the
# contract UC-014 established, for the same reason: an absent key makes the client
# branch on undefined, and "zero" is not "does not exist".
@pytest.mark.asyncio
async def test_every_status_and_category_key_is_present_with_zeros():
    response = await _controller(_repo()).summarize(user_id=1, role="admin", year=2026)

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


# Twelve entries, January to December, always. The dashboard names the year in the
# card title and puts only the month on the axis, which reads correctly only when
# every response covers exactly one calendar year.
@pytest.mark.asyncio
async def test_the_year_is_always_twelve_months_from_january():
    response = await _controller(_repo()).summarize(user_id=1, role="admin", year=2026)

    assert [month["month"] for month in response["by_month"]] == [
        f"2026-{number:02d}" for number in range(1, 13)
    ]


@pytest.mark.asyncio
async def test_an_empty_month_is_zero_rather_than_absent():
    rows = [{"month": "2026-08", "status": "paid", "count": 2, "amount_in_cents": 5000}]

    response = await _controller(_repo(by_month=rows)).summarize(
        user_id=1, role="admin", year=2026
    )

    january = response["by_month"][0]
    assert january["month"] == "2026-01"
    assert january["count"] == 0
    assert january["by_status"]["paid"] == {"count": 0, "amount_in_cents": 0}


# The month's own totals are summed here, so the client never adds them up and
# never disagrees with the server about them.
@pytest.mark.asyncio
async def test_a_month_total_is_the_sum_of_its_statuses():
    rows = [
        {"month": "2026-08", "status": "paid", "count": 2, "amount_in_cents": 5000},
        {"month": "2026-08", "status": "pending", "count": 1, "amount_in_cents": 1500},
    ]

    response = await _controller(_repo(by_month=rows)).summarize(
        user_id=1, role="admin", year=2026
    )

    august = response["by_month"][7]
    assert august["month"] == "2026-08"
    assert august["count"] == 3
    assert august["amount_in_cents"] == 6500


# A month from another year must not appear even if the repository returned it:
# the series is driven by the calendar, not by the rows.
@pytest.mark.asyncio
async def test_a_month_from_another_year_is_dropped():
    rows = [{"month": "2025-01", "status": "paid", "count": 9, "amount_in_cents": 9000}]

    response = await _controller(_repo(by_month=rows)).summarize(
        user_id=1, role="admin", year=2026
    )

    assert all(month["month"].startswith("2026-") for month in response["by_month"])
    assert all(month["count"] == 0 for month in response["by_month"])


# Half-open window, [Jan 1 of the year, Jan 1 of the next): a closed upper bound
# would have to name the last instant of the year, and "23:59:59" silently drops
# whatever happens in the final second.
@pytest.mark.asyncio
async def test_the_window_is_the_calendar_year_half_open():
    repo = _repo()

    await _controller(repo).summarize(user_id=1, role="admin", year=2026)

    assert repo.summarize_refunds.await_args.kwargs["since"] == datetime(2026, 1, 1)
    assert repo.summarize_refunds.await_args.kwargs["until"] == datetime(2027, 1, 1)


# No year means the current one, and the clock is what decides it.
@pytest.mark.asyncio
async def test_an_absent_year_falls_back_to_the_current_one():
    repo = _repo()

    response = await _controller(repo).summarize(user_id=1, role="admin")

    assert response["year"] == 2026
    assert repo.summarize_refunds.await_args.kwargs["since"] == datetime(2026, 1, 1)


@pytest.mark.asyncio
async def test_the_response_echoes_the_year_and_names_its_type():
    response = await _controller(_repo()).summarize(user_id=1, role="admin", year=2025)

    assert response["type"] == "RefundSummary"
    assert response["year"] == 2025
    assert len(response["by_month"]) == 12


# The picker must offer only years that have something: inviting the user into a
# year that is empty by construction is worse than not offering it.
@pytest.mark.asyncio
async def test_the_available_years_come_from_the_repository():
    response = await _controller(_repo(years=[2024, 2026])).summarize(
        user_id=1, role="admin", year=2026
    )

    assert response["available_years"] == [2024, 2026]


# And they are scoped like everything else: a standard user must not learn which
# years OTHER people have refunds in.
@pytest.mark.asyncio
async def test_the_available_years_are_scoped_to_the_same_target():
    repo = _repo()

    await _controller(repo).summarize(
        user_id=1, role="standard", year=2026, filter_user_id=7
    )

    assert repo.available_years.await_args.args[0] == 1


@pytest.mark.asyncio
async def test_an_admin_without_a_filter_aggregates_everyone():
    repo = _repo()

    response = await _controller(repo).summarize(user_id=1, role="admin", year=2026)

    assert response["scope"] == "all"
    assert repo.summarize_refunds.await_args.kwargs["user_id"] is None


@pytest.mark.asyncio
async def test_an_admin_can_narrow_to_one_requester():
    repo = _repo()

    response = await _controller(repo).summarize(
        user_id=1, role="admin", year=2026, filter_user_id=7
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
        user_id=1, role="standard", year=2026, filter_user_id=7
    )

    assert response["scope"] == "user"
    assert repo.summarize_refunds.await_args.kwargs["user_id"] == 1
