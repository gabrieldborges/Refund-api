from abc import ABC, abstractmethod


class ReceiptFinderControllerInterface(ABC):

    @abstractmethod
    async def find(self, refund_id: int, user_id: int, role: str) -> dict:
        pass
