from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.controllers.interfaces.refund_finder_controller_interface import (
    RefundFinderControllerInterface,
)
from src.controllers.refund_serializer import format_refund_response
from src.errors.types.http_not_found_error import HttpNotFoundError


class RefundFinderController(RefundFinderControllerInterface):
    def __init__(self, refunds_repository: RefundsRepositoryInterface) -> None:
        self.__refunds_repository = refunds_repository

    async def find(self, refund_id: int, user_id: int, role: str) -> dict:
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        # 404 both when the refund doesn't exist AND when it belongs to someone else —
        # a 403 here would confirm "this id exists, it's just not yours", letting an
        # attacker enumerate valid refund ids.
        if not refund or (role != "admin" and refund["user"]["id"] != user_id):
            raise HttpNotFoundError("Refund not found")

        return format_refund_response(refund)
