import os
from src.configs.global_config import upload_info
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest

# Same set as refund_creator_validator: BR-009 covers both receipts. Kept as a
# separate constant rather than imported so that loosening one file's rule does
# not silently loosen the other's.
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}


def refund_payer_validator(http_request: HttpRequest) -> None:
    body = http_request.body

    # By extension, not by the client-supplied Content-Type header: that header
    # comes from whatever HTTP client is uploading and is unreliable in practice.
    extension = os.path.splitext(body.get("filename") or "")[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HttpUnprocessableEntityError("Payment receipt must be JPG, PNG or PDF")

    if len(body.get("content", b"")) > upload_info["MAX_FILE_SIZE_BYTES"]:
        raise HttpUnprocessableEntityError("Payment receipt must be smaller than 4MB")
