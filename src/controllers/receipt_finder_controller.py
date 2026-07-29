# pylint: disable=duplicate-code
# Shares its "404 for both missing and not-yours" guard with
# RefundFinderController; a shared helper would be more machinery than the
# problem needs, and the rule is deliberately identical.
import mimetypes
from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.receipt_finder_controller_interface import (
    ReceiptFinderControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class ReceiptFinderController(ReceiptFinderControllerInterface):
    def __init__(
        self,
        refunds_repository: RefundsRepositoryInterface,
        receipt_storage: FileStorageInterface,
    ) -> None:
        self.__refunds_repository = refunds_repository
        self.__receipt_storage = receipt_storage

    async def find(self, refund_id: int, user_id: int, role: str) -> dict:
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        # Same rule as RefundFinderController: 404 for both "doesn't exist" and
        # "not yours", never a 403 that would confirm the id is real.
        if not refund or (role != "admin" and refund["user"]["id"] != user_id):
            raise HttpNotFoundError("Refund not found")

        filename = refund["filename"]

        try:
            content = self.__receipt_storage.read(filename)
        except FileNotFoundError as exception:
            # The row survived but the file did not. Reusing the message keeps
            # this indistinguishable from an unknown id.
            raise HttpNotFoundError("Refund not found") from exception

        return {"content": content, "media_type": self.__media_type(filename)}

    def __media_type(self, filename: str) -> str:
        # Derived from the stored extension, never from a client header — the
        # same reason the upload validators refuse to trust Content-Type.
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"
