from abc import ABC, abstractmethod


class UserFinderControllerInterface(ABC):

    @abstractmethod
    async def find(self, user_id: int, role: str) -> dict:
        pass
