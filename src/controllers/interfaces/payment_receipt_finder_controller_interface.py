from abc import ABC, abstractmethod


class PaymentReceiptFinderControllerInterface(ABC):

    @abstractmethod
    async def find(self, refund_id: int, user_id: int, role: str) -> dict:
        pass
