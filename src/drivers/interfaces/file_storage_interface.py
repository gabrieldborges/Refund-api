from abc import ABC, abstractmethod


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
