import pytest
from src.configs.settings import settings
from src.drivers.file_storage import FileStorage
from src.drivers.s3_file_storage import S3FileStorage
from .storage_factory import build_storage


# FOUND BY COVERAGE (Item 26). build_storage reported 73%: line 29 — the
# `return S3FileStorage(name)` branch — had never executed. The S3 integration
# tests construct S3FileStorage DIRECTLY, so the factory was never asked for
# one. That is the branch a production deployment takes, and nothing had ever
# run it.
def test_the_s3_backend_is_selected_by_configuration(monkeypatch):
    monkeypatch.setattr(settings, "storage_backend", "s3")

    assert isinstance(build_storage("receipts"), S3FileStorage)


def test_the_local_backend_is_the_default(monkeypatch):
    monkeypatch.setattr(settings, "storage_backend", "local")

    assert isinstance(build_storage("receipts"), FileStorage)


# The other uncovered line: an unknown name must be refused rather than joined
# into a path as free text — the guard that keeps a storage name from ever
# walking out of the upload directories.
def test_an_unknown_storage_name_is_refused():
    with pytest.raises(ValueError):
        build_storage("../../etc")
