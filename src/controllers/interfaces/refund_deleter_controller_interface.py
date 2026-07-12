from abc import ABC, abstractmethod


class RefundDeleterControllerInterface(ABC):

    @abstractmethod
    async def delete(self, refund_id: int, user_id: int, role: str) -> dict:
        pass
