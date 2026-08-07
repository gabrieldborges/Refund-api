import os
import uuid
from urllib.parse import quote
from src.configs.settings import settings
from src.drivers.jwt_handler import JwtHandler
from .interfaces.file_storage_interface import FileStorageInterface


class FileStorage(FileStorageInterface):
    # The directory arrives through the constructor instead of being read from
    # config here: receipts and avatars need different folders but identical
    # behaviour, and one implementation is one place to fix a storage bug.
    #
    # `name` is the logical bucket ("receipts", "avatars", "payments"). It is
    # what a signed URL carries and what the /files route looks up to find this
    # directory again — never a path fragment taken from a request, so a forged
    # or malformed name cannot walk out of the upload directories.
    def __init__(self, directory: str, name: str) -> None:
        self.__directory = directory
        self.__name = name

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
        # object-storage item (22) invalidated. The 4MB upload ceiling keeps
        # holding a whole file in memory cheap.
        path = os.path.join(self.__directory, filename)

        with open(path, "rb") as file:
            return file.read()

    def delete(self, filename: str) -> None:
        path = os.path.join(self.__directory, filename)
        if os.path.exists(path):
            os.remove(path)

    def get_url(self, filename: str) -> str:
        """A short-lived signed URL pointing back at this API.

        Local disk has no provider to sign for it, so this mints the signature
        itself: a JWT carrying the storage name and the filename, which
        /files/{storage}/{filename} validates before serving the bytes. Same
        key and same algorithm as the login token, deliberately — the project
        signs in one place.

        The claims are checked against the path by the route, so a token issued
        for one file cannot be replayed against another.
        """
        token = JwtHandler().create_short_lived_token(
            {"storage": self.__name, "file": filename},
            settings.file_url_ttl_seconds,
        )
        base = settings.public_base_url.rstrip("/")
        return f"{base}/files/{self.__name}/{quote(filename)}?token={token}"
