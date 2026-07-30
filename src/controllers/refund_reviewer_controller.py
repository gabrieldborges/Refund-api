# pylint: disable=duplicate-code
# Shares its response envelope shape with RefundFinderController; a shared
# helper would be more machinery than the problem needs for a 4-line dict.
from typing import Optional
from src.models.settings.unit_of_work import UnitOfWork
from src.controllers.interfaces.refund_reviewer_controller_interface import (
    RefundReviewerControllerInterface,
)
from src.errors.types.http_forbidden_error import HttpForbiddenError
from src.errors.types.http_not_found_error import HttpNotFoundError
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError


class RefundReviewerController(RefundReviewerControllerInterface):
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self.__unit_of_work = unit_of_work

    async def review(
        self,
        refund_id: int,
        reviewer_id: int,
        role: str,
        status: str,
        reason: Optional[str],
    ) -> dict:
        # Role first, before any database access. A check that never queries
        # cannot leak whether the id exists, so a standard user gets an identical
        # 403 for a real and for an invented id — the same anti-enumeration
        # reasoning behind BR-013's 404.
        if role != "admin":
            raise HttpForbiddenError("Only administrators can review refunds")

        async with self.__unit_of_work as unit_of_work:
            refund = await unit_of_work.refunds.select_for_update(refund_id)

            if not refund:
                raise HttpNotFoundError("Refund not found")

            # BR-016 — segregation of duties. A 403 is safe here: whoever reached
            # this point is already an admin and, by BR-012, already sees every
            # refund, so there is nothing left to leak.
            if refund["user_id"] == reviewer_id:
                raise HttpForbiddenError("You cannot review your own refund")

            current_status = refund["status"]

            # BR-017 (amended) needs two checks now, not one. "paid" is terminal:
            # money already moved, so no review may leave it, regardless of the
            # target. That is a different rule from "no change to record", which
            # is why it gets its own error instead of folding into the check
            # below. Order matters too — a paid refund with status == "paid"
            # would otherwise never reach it, since the target is always
            # {approved, rejected} and can never equal "paid".
            if current_status == "paid":
                raise HttpUnprocessableEntityError("Refund is already paid and cannot be reviewed")

            if current_status == status:
                raise HttpUnprocessableEntityError(f"Refund is already {status}")

            await unit_of_work.refunds.update_status(refund_id, status)
            await unit_of_work.reviews.insert_review(
                refund_id=refund_id,
                reviewer_id=reviewer_id,
                from_status=current_status,
                to_status=status,
                reason=reason,
            )
            await unit_of_work.commit()

        return self.__format_response(refund, status)

    def __format_response(self, refund: dict, status: str) -> dict:
        created_at = refund.get("created_at")
        return {
            "type": "Refund",
            "count": 1,
            "attributes": {
                **refund,
                "status": status,
                "created_at": created_at.isoformat() if created_at else None,
            },
        }
