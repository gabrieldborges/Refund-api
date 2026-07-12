from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.controllers.interfaces.refund_finder_controller_interface import (
    RefundFinderControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class RefundFinderController(RefundFinderControllerInterface):
    def __init__(self, refunds_repository: RefundsRepositoryInterface) -> None:
        self.__refunds_repository = refunds_repository

    async def find(self, refund_id: int, user_id: int, role: str) -> dict:
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        # 404 both when the refund doesn't exist AND when it belongs to someone else —
        # a 403 here would confirm "this id exists, it's just not yours", letting an
        # attacker enumerate valid refund ids.
        if not refund or (role != "admin" and refund["user_id"] != user_id):
            raise HttpNotFoundError("Refund not found")

        return self.__format_response(refund)

    def __format_response(self, refund: dict) -> dict:
        created_at = refund.get("created_at")
        return {
            "type": "Refund",
            "count": 1,
            "attributes": {
                **refund,
                "created_at": created_at.isoformat() if created_at else None,
            },
        }
