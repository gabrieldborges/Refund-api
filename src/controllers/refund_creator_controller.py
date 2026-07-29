from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.refund_creator_controller_interface import (
    RefundCreatorControllerInterface,
)


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

        return self.__format_response(refund_id, refund_info)

    def __format_response(self, refund_id: int, refund_info: dict) -> dict:
        return {
            "type": "Refund",
            "count": 1,
            "attributes": {"id": refund_id, **refund_info}
        }
