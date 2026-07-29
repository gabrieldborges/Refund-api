import pytest
from src.drivers.file_storage import FileStorage


# The directory now arrives through the constructor, so the same class serves
# receipts and avatars. tmp_path is a pytest fixture giving a real temp folder.
def test_save_writes_the_file_into_the_injected_directory(tmp_path):
    storage = FileStorage(str(tmp_path))

    filename = storage.save("comprovante.jpg", b"conteudo")

    assert (tmp_path / filename).read_bytes() == b"conteudo"


# The stored name must not be the uploaded one: two users uploading "foto.jpg"
# would otherwise overwrite each other.
def test_save_returns_a_unique_name_preserving_the_extension(tmp_path):
    storage = FileStorage(str(tmp_path))

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

    receipt_name = FileStorage(str(receipts)).save("a.jpg", b"r")
    avatar_name = FileStorage(str(avatars)).save("b.jpg", b"a")

    assert (receipts / receipt_name).exists()
    assert (avatars / avatar_name).exists()
    assert not (avatars / receipt_name).exists()


def test_delete_removes_the_file(tmp_path):
    storage = FileStorage(str(tmp_path))
    filename = storage.save("a.jpg", b"x")

    storage.delete(filename)

    assert not (tmp_path / filename).exists()


# Deleting an already-missing file must not raise: the delete path runs after a
# database delete, and blowing up there would fail a request that already
# succeeded.
def test_delete_is_silent_when_the_file_does_not_exist(tmp_path):
    FileStorage(str(tmp_path)).delete("nao-existe.jpg")


def test_read_returns_the_stored_bytes(tmp_path):
    storage = FileStorage(str(tmp_path))
    filename = storage.save("comprovante.jpg", b"conteudo binario")

    assert storage.read(filename) == b"conteudo binario"


# The driver lets FileNotFoundError surface instead of inventing a domain error:
# it does not know what "missing" means to whoever called it. The controller
# translates it into the 404 that fits its use case.
def test_read_raises_when_the_file_does_not_exist(tmp_path):
    storage = FileStorage(str(tmp_path))

    with pytest.raises(FileNotFoundError):
        storage.read("nao-existe.jpg")
