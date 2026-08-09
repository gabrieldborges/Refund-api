from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, NamedTuple


class StoredFile(NamedTuple):
    """What a listing needs to know about a file, and nothing more.

    `modified_at` is here because the orphan sweep (Item 28) cannot decide
    anything without it: a file written two seconds ago whose transaction has
    not committed yet looks exactly like an orphan, and deleting it would
    destroy a valid receipt mid-flight.
    """

    name: str
    modified_at: datetime


class FileStorageInterface(ABC):

    @abstractmethod
    def save(self, original_filename: str, content: bytes) -> str:
        pass

    @abstractmethod
    def read(self, filename: str) -> bytes:
        pass

    @abstractmethod
    def delete(self, filename: str) -> None:
        pass

    @abstractmethod
    def get_url(self, filename: str) -> str:
        """A URL a browser can fetch directly, with no Authorization header.

        This is the whole point of Item 22's signed URLs: an <img> tag cannot
        send a bearer token, which is why the previous design had the API read
        the bytes and stream them back on every single image.

        Both implementations sign, differently: S3 uses the provider's
        presigned URL, local storage mints a short-lived JWT pointing at a
        route of this API. Either way the permission lives in the link and it
        expires — the caller has already checked authorization by the time it
        asks for one.
        """

    @abstractmethod
    def list_files(self) -> List[StoredFile]:
        """Everything currently stored, with when it was last written.

        Added for the orphan sweep. Reconciliation is the one operation that
        has to look at storage from the outside — every other caller already
        knows the filename it wants, because a database row told it.
        """
