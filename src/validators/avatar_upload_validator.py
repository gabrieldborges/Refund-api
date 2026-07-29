import os
from src.configs.global_config import upload_info
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest

# PDF is deliberately absent: it is a valid receipt but cannot be shown as an
# avatar. Same 4MB ceiling as the receipt — a separate constant would only earn
# its place once the two limits need to differ.
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def avatar_upload_validator(http_request: HttpRequest) -> None:
    body = http_request.body

    # Checked by extension, not by the client-supplied Content-Type: that header
    # is set by whatever HTTP client is uploading and is unreliable in practice.
    extension = os.path.splitext(body.get("filename") or "")[1].lower()
    if extension not in ALLOWED_AVATAR_EXTENSIONS:
        raise HttpUnprocessableEntityError("Avatar must be JPG or PNG")

    if len(body.get("content", b"")) > upload_info["MAX_FILE_SIZE_BYTES"]:
        raise HttpUnprocessableEntityError("Avatar must be smaller than 4MB")
