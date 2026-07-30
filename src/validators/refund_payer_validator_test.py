import pytest
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest
from .refund_payer_validator import refund_payer_validator


def build_request(filename="proof.pdf", content=b"x"):
    return HttpRequest(body={"filename": filename, "content": content})


# BR-009 extended: the payment receipt obeys the same format rule as the
# expense receipt.
def test_accepts_the_allowed_extensions():
    for filename in ("proof.jpg", "proof.jpeg", "proof.png", "proof.pdf"):
        refund_payer_validator(build_request(filename=filename))


# Validated by extension, never by the client-supplied Content-Type: that
# header is set by whatever HTTP client is uploading and is unreliable.
def test_rejects_a_disallowed_extension():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_payer_validator(build_request(filename="proof.exe"))


def test_rejects_a_missing_file():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_payer_validator(build_request(filename=""))


def test_rejects_a_file_over_the_size_ceiling():
    oversized = b"x" * (4 * 1024 * 1024 + 1)
    with pytest.raises(HttpUnprocessableEntityError):
        refund_payer_validator(build_request(content=oversized))
