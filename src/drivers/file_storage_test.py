from datetime import datetime, timezone
import pytest
from src.configs.settings import settings
from src.drivers.jwt_handler import JwtHandler
from .file_storage import FileStorage


# The directory now arrives through the constructor, so the same class serves
# receipts and avatars. tmp_path is a pytest fixture giving a real temp folder.
def test_save_writes_the_file_into_the_injected_directory(tmp_path):
    storage = FileStorage(str(tmp_path), "receipts")

    filename = storage.save("comprovante.jpg", b"conteudo")

    assert (tmp_path / filename).read_bytes() == b"conteudo"


# The stored name must not be the uploaded one: two users uploading "foto.jpg"
# would otherwise overwrite each other.
def test_save_returns_a_unique_name_preserving_the_extension(tmp_path):
    storage = FileStorage(str(tmp_path), "receipts")

    first = storage.save("foto.jpg", b"a")
    second = storage.save("foto.jpg", b"b")

    assert first != second
    assert first.endswith(".jpg") and second.endswith(".jpg")
    assert "foto" not in first


def test_two_storages_write_to_their_own_directories(tmp_path):
    receipts = tmp_path / "receipts"
    avatars = tmp_path / "avatars"
    receipts.mkdir()
    avatars.mkdir()

    receipt_name = FileStorage(str(receipts), "receipts").save("a.jpg", b"r")
    avatar_name = FileStorage(str(avatars), "receipts").save("b.jpg", b"a")

    assert (receipts / receipt_name).exists()
    assert (avatars / avatar_name).exists()
    assert not (avatars / receipt_name).exists()


def test_delete_removes_the_file(tmp_path):
    storage = FileStorage(str(tmp_path), "receipts")
    filename = storage.save("a.jpg", b"x")

    storage.delete(filename)

    assert not (tmp_path / filename).exists()


# Deleting an already-missing file must not raise: the delete path runs after a
# database delete, and blowing up there would fail a request that already
# succeeded.
def test_delete_is_silent_when_the_file_does_not_exist(tmp_path):
    FileStorage(str(tmp_path), "receipts").delete("nao-existe.jpg")


def test_read_returns_the_stored_bytes(tmp_path):
    storage = FileStorage(str(tmp_path), "receipts")
    filename = storage.save("comprovante.jpg", b"conteudo binario")

    assert storage.read(filename) == b"conteudo binario"


# The driver lets FileNotFoundError surface instead of inventing a domain error:
# it does not know what "missing" means to whoever called it. The controller
# translates it into the 404 that fits its use case.
def test_read_raises_when_the_file_does_not_exist(tmp_path):
    storage = FileStorage(str(tmp_path), "receipts")

    with pytest.raises(FileNotFoundError):
        storage.read("nao-existe.jpg")


# Item 22 — the local backend has no provider to sign for it, so it mints its
# own: a short-lived JWT naming the storage and the file, pointing at this
# API's /files route. Nothing here is readable without that signature.
def test_get_url_points_at_the_files_route_with_a_token(tmp_path):
    storage = FileStorage(str(tmp_path), "receipts")

    url = storage.get_url("abc.png")

    assert "/files/receipts/abc.png" in url
    assert "token=" in url


# The token must bind to THIS file. A signature that did not name the file
# would be a key to every file in the bucket.
def test_the_token_names_the_storage_and_the_file(tmp_path):
    storage = FileStorage(str(tmp_path), "receipts")

    url = storage.get_url("abc.png")
    token = url.split("token=")[1]
    claims = JwtHandler().decode_jwt_token(token)

    assert claims["storage"] == "receipts"
    assert claims["file"] == "abc.png"


# The permission has to expire. A signed URL that never expires is the
# capability URL that ADR-003 removed in the first place.
def test_the_token_expires(tmp_path):
    storage = FileStorage(str(tmp_path), "receipts")

    token = storage.get_url("abc.png").split("token=")[1]
    claims = JwtHandler().decode_jwt_token(token)

    assert "exp" in claims
    remaining = claims["exp"] - datetime.now(timezone.utc).timestamp()
    assert 0 < remaining <= settings.file_url_ttl_seconds
