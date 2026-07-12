from abc import ABC, abstractmethod


class RefundFinderControllerInterface(ABC):

    @abstractmethod
    async def find(self, refund_id: int, user_id: int, role: str) -> dict:
        pass
