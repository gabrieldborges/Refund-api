from src.configs.global_config import upload_info
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest

ALLOWED_CATEGORIES = {"food", "lodging", "transport", "service", "equipment"}


def refund_creator_validator(http_request: HttpRequest) -> None:
    body = http_request.body

    if not body.get("name") or not str(body["name"]).strip():
        raise HttpUnprocessableEntityError("Name is required")

    if body.get("category") not in ALLOWED_CATEGORIES:
        raise HttpUnprocessableEntityError(
            f"Category must be one of: {', '.join(sorted(ALLOWED_CATEGORIES))}"
        )

    if body.get("amount") is None or body["amount"] <= 0:
        raise HttpUnprocessableEntityError("Amount must be greater than zero")

    if body.get("content_type") not in upload_info["ALLOWED_CONTENT_TYPES"]:
        raise HttpUnprocessableEntityError("Receipt file must be JPG, PNG or PDF")

    if len(body.get("content", b"")) > upload_info["MAX_FILE_SIZE_BYTES"]:
        raise HttpUnprocessableEntityError("Receipt file must be smaller than 4MB")
