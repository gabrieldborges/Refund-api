from abc import ABC, abstractmethod


class RefundReviewListerControllerInterface(ABC):

    @abstractmethod
    async def list(self, refund_id: int, user_id: int, role: str) -> dict:
        pass
