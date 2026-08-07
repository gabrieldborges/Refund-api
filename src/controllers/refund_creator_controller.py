from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.refund_creator_controller_interface import (
    RefundCreatorControllerInterface,
)
from src.controllers.refund_serializer import format_refund_response
from src.controllers.file_cleanup import delete_quietly


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

        # The file is already on disk and nothing points at it yet. If the
        # insert fails — a foreign key violation, the engine's 3s lock_timeout
        # expiring, the database simply being down — that file would stay
        # there forever with no row referencing it. Seven such orphans were
        # once found and removed by hand; this is the compensation that keeps
        # them from being created in the first place.
        try:
            refund_id = await self.__refunds_repository.insert_refund(refund_info)
        except Exception:
            delete_quietly(
                self.__receipt_storage, filename, "refund receipt, insert failed"
            )
            raise

        # The compensation above deliberately stops at the insert. insert_refund
        # commits, so from this line on the row EXISTS and points at this file:
        # deleting it because a later step failed would destroy the receipt of a
        # real refund. Same boundary RefundPayerController draws with its
        # `committed` flag, for the same reason.
        #
        # Re-reading gives the columns the database filled in (status) and the
        # joined requester, so this response has the same shape as GET.
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        return format_refund_response(refund)
