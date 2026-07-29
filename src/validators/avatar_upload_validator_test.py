import pytest
from src.errors.types.http_unprocessable_entity_error import HttpUnprocessableEntityError
from src.views.http_types.http_request import HttpRequest
from .avatar_upload_validator import avatar_upload_validator


def valid_body(**overrides) -> dict:
    body = {"filename": "foto.jpg", "content": b"x"}
    body.update(overrides)
    return body


def test_jpg_is_accepted():
    avatar_upload_validator(HttpRequest(body=valid_body()))


def test_png_is_accepted():
    avatar_upload_validator(HttpRequest(body=valid_body(filename="foto.png")))


def test_extension_check_is_case_insensitive():
    avatar_upload_validator(HttpRequest(body=valid_body(filename="FOTO.JPG")))


# PDF is a valid receipt but never a valid avatar.
def test_pdf_is_rejected():
    with pytest.raises(HttpUnprocessableEntityError):
        avatar_upload_validator(HttpRequest(body=valid_body(filename="foto.pdf")))


def test_missing_filename_is_rejected():
    with pytest.raises(HttpUnprocessableEntityError):
        avatar_upload_validator(HttpRequest(body=valid_body(filename=None)))


def test_file_bigger_than_the_limit_is_rejected():
    oversized = b"x" * (4 * 1024 * 1024 + 1)
    with pytest.raises(HttpUnprocessableEntityError):
        avatar_upload_validator(HttpRequest(body=valid_body(content=oversized)))
