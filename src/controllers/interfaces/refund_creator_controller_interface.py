from abc import ABC, abstractmethod


class RefundCreatorControllerInterface(ABC):

    @abstractmethod
    async def create(self, refund_data: dict, user_id: int) -> dict:
        pass
