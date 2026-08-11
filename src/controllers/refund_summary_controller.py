from datetime import datetime
from typing import Callable, Optional
from src.models.repositories.interfaces.refunds_repository_interface import (
    RefundsRepositoryInterface,
)
from src.controllers.interfaces.refund_summary_controller_interface import (
    RefundSummaryControllerInterface,
)
from src.validators.refund_creator_validator import ALLOWED_CATEGORIES

# Same tuple, same order, same reason as refund_stats_finder_controller: the
# response publishes a FIXED set of keys so the client never branches on a missing
# one. "Zero" and "does not exist" are different claims, and a chart cannot tell
# them apart from an absent key.
ALL_STATUSES = ("pending", "approved", "paid", "rejected")
MONTHS_IN_YEAR = 12


class RefundSummaryController(RefundSummaryControllerInterface):
    def __init__(
        self,
        refunds_repository: RefundsRepositoryInterface,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self.__refunds_repository = refunds_repository
        # Injected so a test can fix "today" without freezing datetime for the
        # whole process — and so the default-year assertions do not start failing
        # by themselves at the turn of a year.
        self.__clock = clock

    async def summarize(
        self,
        user_id: int,
        role: str,
        year: Optional[int] = None,
        filter_user_id: Optional[int] = None,
    ) -> dict:
        # Same scope idiom as refund_lister_controller: an admin sees everyone and
        # may narrow to one requester; for a standard user the parameter is
        # IGNORED, not rejected — they are already locked to themselves, so there
        # is nothing to leak and no new error path to document.
        target = filter_user_id if role == "admin" else user_id

        # A CALENDAR year, not a rolling window. The dashboard names the year in
        # each card title and shows only the month on the axis, which only reads
        # correctly when every response covers Jan–Dec of one year: a rolling
        # window would put two different years on one axis of bare month names.
        selected = year or self.__clock().year

        (
            by_status,
            by_category,
            month_rows,
        ) = await self.__refunds_repository.summarize_refunds(
            user_id=target,
            since=datetime(selected, 1, 1),
            until=datetime(selected + 1, 1, 1),
        )

        return {
            "type": "RefundSummary",
            "scope": "all" if target is None else "user",
            "year": selected,
            # Only the years that have something, so the picker never invites the
            # user into a chart that is empty by construction.
            "available_years": await self.__refunds_repository.available_years(target),
            "by_status": self.__filled(by_status, ALL_STATUSES),
            "by_category": self.__filled(by_category, sorted(ALLOWED_CATEGORIES)),
            "by_month": self.__months(selected, month_rows),
        }

    def __filled(self, grouped: dict, keys) -> dict:
        # A fresh dict per key: a shared literal would let one caller's mutation
        # reach every other zero in the response.
        return {
            key: grouped.get(key) or {"count": 0, "amount_in_cents": 0} for key in keys
        }

    def __months(self, year: int, rows: list) -> list:
        by_month: dict = {}
        for row in rows:
            bucket = by_month.setdefault(row["month"], {})
            bucket[row["status"]] = {
                "count": row["count"],
                "amount_in_cents": row["amount_in_cents"],
            }

        months = []
        for number in range(1, MONTHS_IN_YEAR + 1):
            key = f"{year}-{number:02d}"
            statuses = self.__filled(by_month.get(key, {}), ALL_STATUSES)
            # Always twelve entries, January to December, zeros included. A gap in
            # the series would make the line chart lie about its slope, and a
            # short first month would read as a drop that never happened.
            #
            # The month's totals are summed HERE, so the client never adds them up
            # and never disagrees with the server about them. Driven by the
            # calendar and not by `rows`, which is also what drops a month the
            # repository returned from outside the year.
            months.append(
                {
                    "month": key,
                    "count": sum(entry["count"] for entry in statuses.values()),
                    "amount_in_cents": sum(
                        entry["amount_in_cents"] for entry in statuses.values()
                    ),
                    "by_status": statuses,
                }
            )
        return months
