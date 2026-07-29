from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.refund_creator_controller_interface import (
    RefundCreatorControllerInterface,
)
from src.controllers.refund_serializer import serialize_refund


class RefundCreatorController(RefundCreatorControllerInterface):
    def __init__(
        self,
        refunds_repository: RefundsRepositoryInterface,
        receipt_storage: FileStorageInterface,
    ) -> None:
        self.__refunds_repository = refunds_repository
        self.__receipt_storage = receipt_storage

    async def create(self, refund_data: dict, user_id: int) -> dict:
        filename = self.__receipt_storage.save(refund_data["filename"], refund_data["content"])

        refund_info = {
            "user_id": user_id,
            "name": refund_data["name"],
            "category": refund_data["category"],
            "amount_in_cents": round(refund_data["amount"] * 100),
            "filename": filename,
        }

        refund_id = await self.__refunds_repository.insert_refund(refund_info)

        # Re-reading gives the columns the database filled in (status) and the
        # joined requester, so this response has the same shape as GET.
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        return self.__format_response(refund)

    def __format_response(self, refund: dict) -> dict:
        return {
            "type": "Refund",
            "count": 1,
            "attributes": serialize_refund(refund),
        }
