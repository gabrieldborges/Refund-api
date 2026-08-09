# pylint: disable=w0621
# The route handler is still called directly, and that is now a CHOICE rather
# than a limitation — Item 25 added httpx, so TestClient is available.
#
# These stay unit tests because they cover LOGIC (signature check, claim/path
# match, traversal guard) and run in milliseconds without containers. What they
# could never cover — that the route is wired up at all — is covered now by
# src/test_integration/api_test.py, which fetches a signed URL over real HTTP
# and checks that a tampered one is refused. Rewriting these as integration
# tests would trade fast coverage for slow coverage of the same logic.
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from src.drivers.jwt_handler import JwtHandler
from .file_routes import serve_signed_file


def a_token(storage="receipts", filename="abc.png", ttl_seconds=300):
    return JwtHandler().create_short_lived_token(
        {"storage": storage, "file": filename}, ttl_seconds
    )


@pytest.fixture
def storage_returning_bytes():
    storage = MagicMock()
    storage.read = MagicMock(return_value=b"file bytes")
    return storage


# Happy path: a valid signature for this exact file serves the bytes, with no
# Authorization header anywhere — which is the entire reason signed URLs exist,
# since an <img> tag cannot send one.
@pytest.mark.asyncio
async def test_a_valid_token_serves_the_file(storage_returning_bytes):
    with patch("src.main.routes.file_routes.build_storage", return_value=storage_returning_bytes):
        response = await serve_signed_file("receipts", "abc.png", token=a_token())

    assert response.body == b"file bytes"
    assert response.media_type == "image/png"


# The media type moved here from the controller, and the rule that came with it
# is unchanged: derived from the stored extension, never from a client header.
@pytest.mark.asyncio
async def test_the_media_type_comes_from_the_stored_extension(storage_returning_bytes):
    with patch("src.main.routes.file_routes.build_storage", return_value=storage_returning_bytes):
        response = await serve_signed_file(
            "receipts", "doc.pdf", token=a_token(filename="doc.pdf")
        )

    assert response.media_type == "application/pdf"


# THE ATTACK THIS EXISTS TO STOP. A token is issued per file; if the route only
# checked that the signature was valid, any one token would read every file.
@pytest.mark.asyncio
async def test_a_token_for_another_file_is_refused(storage_returning_bytes):
    token = a_token(filename="mine.png")

    with patch("src.main.routes.file_routes.build_storage", return_value=storage_returning_bytes):
        with pytest.raises(HTTPException) as error:
            await serve_signed_file("receipts", "someone-elses.png", token=token)

    assert error.value.status_code == 404
    storage_returning_bytes.read.assert_not_called()


# Same for the bucket: a receipt token must not read an avatar.
@pytest.mark.asyncio
async def test_a_token_for_another_storage_is_refused(storage_returning_bytes):
    token = a_token(storage="receipts", filename="abc.png")

    with patch("src.main.routes.file_routes.build_storage", return_value=storage_returning_bytes):
        with pytest.raises(HTTPException) as error:
            await serve_signed_file("avatars", "abc.png", token=token)

    assert error.value.status_code == 404


# Unsigned access is the whole thing being prevented; a made-up token is not a
# 401 but a 404, so a stale link cannot confirm the file exists.
@pytest.mark.asyncio
async def test_a_forged_token_is_refused(storage_returning_bytes):
    with patch("src.main.routes.file_routes.build_storage", return_value=storage_returning_bytes):
        with pytest.raises(HTTPException) as error:
            await serve_signed_file("receipts", "abc.png", token="not-a-jwt")

    assert error.value.status_code == 404


# The permission must actually expire. Without this the URL is the permanent
# capability link ADR-003 removed.
@pytest.mark.asyncio
async def test_an_expired_token_is_refused(storage_returning_bytes):
    expired = a_token(ttl_seconds=-1)

    with patch("src.main.routes.file_routes.build_storage", return_value=storage_returning_bytes):
        with pytest.raises(HTTPException) as error:
            await serve_signed_file("receipts", "abc.png", token=expired)

    assert error.value.status_code == 404
    storage_returning_bytes.read.assert_not_called()


# A filename is a name, not a path. Even signed — and the signer is us — a
# separator must not be allowed to walk out of the upload directory.
@pytest.mark.asyncio
async def test_a_filename_containing_a_path_is_refused(storage_returning_bytes):
    traversal = "../../.env"
    token = a_token(filename=traversal)

    with patch("src.main.routes.file_routes.build_storage", return_value=storage_returning_bytes):
        with pytest.raises(HTTPException) as error:
            await serve_signed_file("receipts", traversal, token=token)

    assert error.value.status_code == 404
    storage_returning_bytes.read.assert_not_called()


# The file being gone answers exactly like everything else above.
@pytest.mark.asyncio
async def test_a_missing_file_is_not_found():
    storage = MagicMock()
    storage.read = MagicMock(side_effect=FileNotFoundError())

    with patch("src.main.routes.file_routes.build_storage", return_value=storage):
        with pytest.raises(HTTPException) as error:
            await serve_signed_file("receipts", "abc.png", token=a_token())

    assert error.value.status_code == 404
