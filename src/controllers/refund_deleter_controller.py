from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.drivers.interfaces.receipt_storage_interface import ReceiptStorageInterface
from src.controllers.interfaces.refund_deleter_controller_interface import (
    RefundDeleterControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class RefundDeleterController(RefundDeleterControllerInterface):
    def __init__(
        self,
        refunds_repository: RefundsRepositoryInterface,
        receipt_storage: ReceiptStorageInterface,
    ) -> None:
        self.__refunds_repository = refunds_repository
        self.__receipt_storage = receipt_storage

    async def delete(self, refund_id: int, user_id: int, role: str) -> dict:
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        # Same rule as RefundFinderController: 404 for both "doesn't exist" and
        # "not yours", never a 403 that would confirm the id is real.
        if not refund or (role != "admin" and refund["user_id"] != user_id):
            raise HttpNotFoundError("Refund not found")

        await self.__refunds_repository.delete_refund(refund_id)
        self.__receipt_storage.delete(refund["filename"])

        return self.__format_response(refund_id)

    def __format_response(self, refund_id: int) -> dict:
        return {
            "type": "Refund",
            "count": 1,
            "attributes": {"id": refund_id, "deleted": True},
        }
