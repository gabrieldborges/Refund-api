from calendar import monthrange
from datetime import date
from typing import Optional
from src.models.repositories.interfaces.refunds_repository_interface import (
    RefundsRepositoryInterface,
)
from src.controllers.interfaces.refund_daily_counts_controller_interface import (
    RefundDailyCountsControllerInterface,
)


class RefundDailyCountsController(RefundDailyCountsControllerInterface):
    def __init__(self, refunds_repository: RefundsRepositoryInterface) -> None:
        self.__refunds_repository = refunds_repository

    async def count(
        self,
        user_id: int,
        role: str,
        year: int,
        month: int,
        filter_user_id: Optional[int] = None,
    ) -> dict:
        # Same scope idiom as refund_lister_controller: an admin sees everyone and
        # may narrow to one requester; for a standard user the parameter is
        # IGNORED, not rejected — they are already locked to themselves, so there
        # is nothing to leak and no new error path to document.
        target = filter_user_id if role == "admin" else user_id

        first = date(year, month, 1)
        # monthrange, and NOT a table of month lengths: February is 28 or 29 and
        # getting that from the calendar module is the difference between a
        # calendar that is right every year and one that is right most years.
        _, days_in_month = monthrange(year, month)
        after_last = (
            date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        )

        counted = await self.__refunds_repository.count_by_day(
            user_id=target, since=first, until=after_last
        )

        return {
            "type": "RefundDailyCounts",
            "scope": "all" if target is None else "user",
            "month": f"{year}-{month:02d}",
            # Every day of the month, zeros included, driven by the calendar rather
            # than by the rows. The client draws a grid: a missing day would make it
            # branch on undefined, and a day that exists with zero refunds is a
            # different claim from a day that does not exist.
            "days": [
                {
                    "date": date(year, month, day).isoformat(),
                    "count": counted.get(date(year, month, day).isoformat(), 0),
                }
                for day in range(1, days_in_month + 1)
            ],
        }
