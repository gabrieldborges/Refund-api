import math
from typing import Optional
from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.controllers.interfaces.refund_lister_controller_interface import (
    RefundListerControllerInterface,
)
from src.controllers.refund_serializer import serialize_refund


class RefundListerController(RefundListerControllerInterface):
    def __init__(self, refunds_repository: RefundsRepositoryInterface) -> None:
        self.__refunds_repository = refunds_repository

    async def list(
        self,
        page: int,
        per_page: int,
        user_id: int,
        role: str,
        name: Optional[str] = None,
        status: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ) -> dict:
        # Authorization rule lives here, not in the repository: an admin can see
        # everyone's refunds (no user_id filter), a standard user only their own.
        filter_user_id = None if role == "admin" else user_id

        refunds, total, total_amount = await self.__refunds_repository.select_refunds(
            page=page, per_page=per_page, name=name, user_id=filter_user_id,
            status=status, sort=sort, order=order,
        )

        return self.__format_response(refunds, total, total_amount, page, per_page)

    def __format_response(
        self, refunds: list, total: int, total_amount: int, page: int, per_page: int
    ) -> dict:
        return {
            "type": "Refund",
            "count": len(refunds),
            "total": total,
            "sum_amount_in_cents": total_amount,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total / per_page) if total else 0,
            "attributes": [serialize_refund(refund) for refund in refunds],
        }
