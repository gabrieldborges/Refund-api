"""Picks the storage backend from configuration.

The eight composers used to write FileStorage(settings.upload_dir) directly,
which hard-wired the choice at every call site. They now ask for a logical
bucket by name and this decides — so switching a deployment to object storage
is an environment variable, not a code change.
"""
from src.configs.settings import settings
from src.drivers.file_storage import FileStorage
from src.drivers.interfaces.file_storage_interface import FileStorageInterface
from src.drivers.s3_file_storage import S3FileStorage


# The only place a logical name maps to a real location. The route that serves
# local signed URLs looks names up here too, which is what keeps a name from
# ever being joined into a path as free text.
LOCAL_DIRECTORIES = {
    "receipts": settings.upload_dir,
    "avatars": settings.avatar_dir,
    "payments": settings.payment_dir,
}


def build_storage(name: str) -> FileStorageInterface:
    if name not in LOCAL_DIRECTORIES:
        raise ValueError(f"unknown storage {name!r}")

    if settings.storage_backend == "s3":
        return S3FileStorage(name)

    return FileStorage(LOCAL_DIRECTORIES[name], name)
