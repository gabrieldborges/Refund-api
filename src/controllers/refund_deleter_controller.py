from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.refund_deleter_controller_interface import (
    RefundDeleterControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError


class RefundDeleterController(RefundDeleterControllerInterface):
    def __init__(
        self,
        refunds_repository: RefundsRepositoryInterface,
        receipt_storage: FileStorageInterface,
    ) -> None:
        self.__refunds_repository = refunds_repository
        self.__receipt_storage = receipt_storage

    async def delete(self, refund_id: int, user_id: int, role: str) -> dict:
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        # Same rule as RefundFinderController: 404 for both "doesn't exist" and
        # "not yours", never a 403 that would confirm the id is real.
        if not refund or (role != "admin" and refund["user"]["id"] != user_id):
            raise HttpNotFoundError("Refund not found")

        # BR-015: only a pending refund can be deleted. After a decision the
        # request is immutable to its owner — otherwise deleting would be a way to
        # erase one's own rejection along with its history.
        if refund["status"] != "pending":
            raise HttpUnprocessableEntityError("Only pending refunds can be deleted")

        # This read said "pending", but a review can commit between this line and
        # the DELETE below (it takes select_for_update in its own transaction, so
        # it isn't blocked by this read). The repository re-checks the status as
        # part of the DELETE itself and reports whether it actually removed a row;
        # rowcount == 0 means we lost that race, so raise the same 422 the
        # up-front check above would have raised had it seen the final status.
        deleted_count = await self.__refunds_repository.delete_refund(refund_id)
        if deleted_count == 0:
            raise HttpUnprocessableEntityError("Only pending refunds can be deleted")

        # Only remove the receipt file once we know the row was actually deleted —
        # deleting it after losing the race would destroy the receipt of a refund
        # that a reviewer just decided on and that still exists.
        self.__receipt_storage.delete(refund["filename"])

        return self.__format_response(refund_id)

    def __format_response(self, refund_id: int) -> dict:
        return {
            "type": "Refund",
            "count": 1,
            "attributes": {"id": refund_id, "deleted": True},
        }
