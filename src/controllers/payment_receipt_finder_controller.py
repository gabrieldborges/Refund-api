# pylint: disable=duplicate-code
# Shares its "404 for both missing and not-yours" guard with
# ReceiptFinderController; the rule is deliberately identical.
import mimetypes
from src.models.repositories.interfaces.refunds_repository_interface import RefundsRepositoryInterface
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.controllers.interfaces.payment_receipt_finder_controller_interface import (
    PaymentReceiptFinderControllerInterface,
)
from src.errors.types.http_not_found_error import HttpNotFoundError


class PaymentReceiptFinderController(PaymentReceiptFinderControllerInterface):
    def __init__(
        self,
        refunds_repository: RefundsRepositoryInterface,
        payment_storage: FileStorageInterface,
    ) -> None:
        self.__refunds_repository = refunds_repository
        self.__payment_storage = payment_storage

    async def find(self, refund_id: int, user_id: int, role: str) -> dict:
        refund = await self.__refunds_repository.select_refund_by_id(refund_id)

        if not refund or (role != "admin" and refund["user"]["id"] != user_id):
            raise HttpNotFoundError("Refund not found")

        filename = refund.get("payment_filename")

        # An unpaid refund answers exactly like an unknown one. Saying "this
        # refund exists but is not paid" would leak state to someone who may
        # not be entitled to it, and there is no reason to distinguish.
        if not filename:
            raise HttpNotFoundError("Refund not found")

        try:
            content = self.__payment_storage.read(filename)
        except FileNotFoundError as exception:
            raise HttpNotFoundError("Refund not found") from exception

        return {"content": content, "media_type": self.__media_type(filename)}

    def __media_type(self, filename: str) -> str:
        # Derived from the stored extension, never from a client header.
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"
