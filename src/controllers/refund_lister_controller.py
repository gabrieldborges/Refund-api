import math
from typing import Optional
from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.controllers.interfaces.refund_lister_controller_interface import (
    RefundListerControllerInterface,
)


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
    ) -> dict:
        # Authorization rule lives here, not in the repository: an admin can see
        # everyone's refunds (no user_id filter), a standard user only their own.
        filter_user_id = None if role == "admin" else user_id

        refunds, total = await self.__refunds_repository.select_refunds(
            page=page, per_page=per_page, name=name, user_id=filter_user_id
        )

        return self.__format_response(refunds, total, page, per_page)

    def __format_response(self, refunds: list, total: int, page: int, per_page: int) -> dict:
        return {
            "type": "Refund",
            "count": len(refunds),
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": math.ceil(total / per_page) if total else 0,
            "attributes": [self.__serialize(refund) for refund in refunds],
        }

    # The repository returns created_at as a raw Python datetime (straight from the
    # database row), which JSONResponse can't encode on its own. This is where we
    # convert DB types into JSON-safe ones, since that's an API-boundary concern.
    def __serialize(self, refund: dict) -> dict:
        created_at = refund.get("created_at")
        return {
            **refund,
            "created_at": created_at.isoformat() if created_at else None,
        }
