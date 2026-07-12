import pytest
from src.configs.global_config import upload_info
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest
from .refund_creator_validator import refund_creator_validator


# Builds a well-formed refund body; tests override only the field they want to break.
def valid_body(**overrides):
    body = {
        "name": "Ana Silva",
        "category": "food",
        "amount": 45.90,
        "filename": "receipt.jpg",
        "content": b"x" * 100,
    }
    body.update(overrides)
    return body


# Happy path: a well-formed refund passes without raising anything.
def test_valid_refund_passes_without_raising():
    http_request = HttpRequest(body=valid_body())

    refund_creator_validator(http_request)


def test_missing_name_raises():
    http_request = HttpRequest(body=valid_body(name=""))

    with pytest.raises(HttpUnprocessableEntityError):
        refund_creator_validator(http_request)


def test_category_outside_the_allowed_list_raises():
    http_request = HttpRequest(body=valid_body(category="vacation"))

    with pytest.raises(HttpUnprocessableEntityError):
        refund_creator_validator(http_request)


def test_zero_or_negative_amount_raises():
    http_request = HttpRequest(body=valid_body(amount=0))

    with pytest.raises(HttpUnprocessableEntityError):
        refund_creator_validator(http_request)


# Validated by extension, not by the client-declared Content-Type header — that
# header proved unreliable in practice (Postman sent "application/octet-stream" for
# a real jpg upload, which a content-type-only check would wrongly accept/reject).
def test_disallowed_file_extension_raises():
    http_request = HttpRequest(body=valid_body(filename="malware.exe"))

    with pytest.raises(HttpUnprocessableEntityError):
        refund_creator_validator(http_request)


# Accepts any casing and any of the allowed extensions, not just ".jpg".
@pytest.mark.parametrize("filename", ["receipt.JPG", "receipt.jpeg", "receipt.png", "receipt.pdf"])
def test_allowed_extensions_pass_regardless_of_case(filename):
    http_request = HttpRequest(body=valid_body(filename=filename))

    refund_creator_validator(http_request)


# Reads the limit straight from config and builds content 1 byte over it, so the
# test stays valid even if the value changes later (no duplicated magic number).
def test_file_larger_than_the_limit_raises():
    over_limit = upload_info["MAX_FILE_SIZE_BYTES"] + 1
    http_request = HttpRequest(body=valid_body(content=b"x" * over_limit))

    with pytest.raises(HttpUnprocessableEntityError):
        refund_creator_validator(http_request)
