import os
import uuid
from .interfaces.file_storage_interface import FileStorageInterface


class FileStorage(FileStorageInterface):
    # The directory arrives through the constructor instead of being read from
    # config here: receipts and avatars need different folders but identical
    # behaviour, and one implementation is one place to fix a storage bug.
    def __init__(self, directory: str) -> None:
        self.__directory = directory

    def save(self, original_filename: str, content: bytes) -> str:
        extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{extension}"
        path = os.path.join(self.__directory, unique_filename)

        with open(path, "wb") as file:
            file.write(content)

        return unique_filename

    def read(self, filename: str) -> bytes:
        # Returns bytes rather than a path on purpose: a path would assert that
        # the file lives on a local filesystem, which is exactly the claim the
        # object-storage item (22) will invalidate. The 4MB upload ceiling keeps
        # holding a whole file in memory cheap.
        path = os.path.join(self.__directory, filename)

        with open(path, "rb") as file:
            return file.read()

    def delete(self, filename: str) -> None:
        path = os.path.join(self.__directory, filename)
        if os.path.exists(path):
            os.remove(path)
