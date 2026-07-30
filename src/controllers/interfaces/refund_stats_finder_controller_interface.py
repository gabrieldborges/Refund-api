from abc import ABC, abstractmethod


class RefundStatsFinderControllerInterface(ABC):

    @abstractmethod
    async def find(self, target_user_id: int, user_id: int, role: str) -> dict:
        pass
