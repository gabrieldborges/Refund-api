from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.controllers.interfaces.refund_stats_finder_controller_interface import (
    RefundStatsFinderControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError

# The response always carries these four keys, in this order, even when the
# user has no refund in a given status.
ALL_STATUSES = ("pending", "approved", "paid", "rejected")


class RefundStatsFinderController(RefundStatsFinderControllerInterface):
    def __init__(self, refunds_repository: RefundsRepositoryInterface) -> None:
        self.__refunds_repository = refunds_repository

    async def find(self, target_user_id: int, user_id: int, role: str) -> dict:
        # 404, not 403: a 403 would confirm the user id is real, the same
        # anti-enumeration reasoning behind BR-013.
        if role != "admin" and target_user_id != user_id:
            raise HttpNotFoundError("User not found")

        totals = await self.__refunds_repository.count_by_status(target_user_id)

        return {
            "type": "RefundStats",
            "user_id": target_user_id,
            # No total, of count or of amount. Summing across statuses would add
            # a forecast (pending) to a liability (approved) to a realised
            # expense (paid) to nothing (rejected) — the defect that made the
            # Home's "Total" card meaningless. Rates and averages are divisions
            # of these numbers and belong to the client.
            "by_status": {
                status: totals.get(status, {"count": 0, "amount_in_cents": 0})
                for status in ALL_STATUSES
            },
        }
