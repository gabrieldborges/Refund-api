# ReceiptStorage touches the real filesystem, so instead of mocking open()/os.remove
# (which would barely test anything), we point UPLOAD_DIR at pytest's tmp_path fixture —
# a real, isolated temp directory that pytest creates and cleans up automatically.
import os
import pytest
from src.configs.global_config import upload_info
from .receipt_storage import ReceiptStorage


@pytest.fixture(autouse=True)
def use_tmp_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setitem(upload_info, "UPLOAD_DIR", str(tmp_path))
    return tmp_path


def test_save_writes_the_file_and_returns_a_filename_with_the_original_extension():
    storage = ReceiptStorage()

    filename = storage.save("receipt.jpg", b"fake-image-bytes")

    assert filename.endswith(".jpg")
    saved_path = os.path.join(upload_info["UPLOAD_DIR"], filename)
    assert os.path.exists(saved_path)
    with open(saved_path, "rb") as file:
        assert file.read() == b"fake-image-bytes"


# Two uploads with the same original name must not overwrite each other.
def test_save_generates_a_different_filename_on_each_call():
    storage = ReceiptStorage()

    first = storage.save("receipt.jpg", b"a")
    second = storage.save("receipt.jpg", b"b")

    assert first != second


def test_delete_removes_an_existing_file():
    storage = ReceiptStorage()
    filename = storage.save("receipt.pdf", b"data")
    saved_path = os.path.join(upload_info["UPLOAD_DIR"], filename)
    assert os.path.exists(saved_path)

    storage.delete(filename)

    assert not os.path.exists(saved_path)


# Deleting a refund whose file is already gone must not raise (idempotent cleanup).
def test_delete_does_nothing_when_the_file_does_not_exist():
    storage = ReceiptStorage()

    storage.delete("does-not-exist.jpg")
