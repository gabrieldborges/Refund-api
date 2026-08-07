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

        # Item 22: a signed URL instead of the bytes. The authorization checks
        # above still run — the URL is only minted for a caller already
        # entitled to the file, and it expires in FILE_URL_TTL_SECONDS.
        #
        # WHAT CHANGED IN BEHAVIOUR: this no longer reads the file, so "the row
        # survived but the file did not" is no longer a 404 from HERE; it
        # surfaces when the browser follows the URL. The anti-enumeration
        # property that mattered is intact — "does not exist" and "is not
        # yours" are still indistinguishable, because both are refused before a
        # URL exists. Checking existence would cost a HEAD request per URL
        # against S3, which is most of what this item was trying to avoid.
        return {
            "url": self.__receipt_storage.get_url(filename),
            "media_type": self.__media_type(filename),
        }

    def __media_type(self, filename: str) -> str:
        # Derived from the stored extension, never from a client header — the
        # same reason the upload validators refuse to trust Content-Type. Kept
        # in the response even though the bytes now come from elsewhere: the
        # client has to decide between <img> and <object> BEFORE fetching, and
        # a URL carries no type.
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"
