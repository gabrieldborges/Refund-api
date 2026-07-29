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

    def delete(self, filename: str) -> None:
        path = os.path.join(self.__directory, filename)
        if os.path.exists(path):
            os.remove(path)
