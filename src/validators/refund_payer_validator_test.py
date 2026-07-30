import pytest
from src.configs.global_config import upload_info
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest
from .refund_payer_validator import refund_payer_validator


def build_request(filename="proof.pdf", content=b"x"):
    return HttpRequest(body={"filename": filename, "content": content})


# BR-009 extended: the payment receipt obeys the same format rule as the
# expense receipt.
@pytest.mark.parametrize("filename", ["proof.jpg", "proof.jpeg", "proof.png", "proof.pdf"])
def test_accepts_the_allowed_extensions(filename):
    refund_payer_validator(build_request(filename=filename))


# Accepts any casing and any of the allowed extensions, not just ".jpg".
@pytest.mark.parametrize("filename", ["proof.JPG", "proof.JPEG", "proof.PNG", "proof.PDF"])
def test_allowed_extensions_pass_regardless_of_case(filename):
    refund_payer_validator(build_request(filename=filename))


# Validated by extension, never by the client-supplied Content-Type: that
# header is set by whatever HTTP client is uploading and is unreliable.
def test_rejects_a_disallowed_extension():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_payer_validator(build_request(filename="proof.exe"))


def test_rejects_a_missing_file():
    with pytest.raises(HttpUnprocessableEntityError):
        refund_payer_validator(build_request(filename=""))


# Content of exactly the maximum size should be accepted; off-by-one in the
# boundary check would be caught by this test.
def test_accepts_a_file_at_the_size_ceiling():
    max_size = upload_info["MAX_FILE_SIZE_BYTES"]
    refund_payer_validator(build_request(content=b"x" * max_size))


# Reads the limit straight from config and builds content 1 byte over it, so the
# test stays valid even if the value changes later (no duplicated magic number).
def test_rejects_a_file_over_the_size_ceiling():
    over_limit = upload_info["MAX_FILE_SIZE_BYTES"] + 1
    with pytest.raises(HttpUnprocessableEntityError):
        refund_payer_validator(build_request(content=b"x" * over_limit))
