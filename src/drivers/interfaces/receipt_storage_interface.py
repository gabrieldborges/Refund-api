from abc import ABC, abstractmethod


class ReceiptStorageInterface(ABC):

    @abstractmethod
    def save(self, original_filename: str, content: bytes) -> str:
        pass

    @abstractmethod
    def delete(self, filename: str) -> None:
        pass
