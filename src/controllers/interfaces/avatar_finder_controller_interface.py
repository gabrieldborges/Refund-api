from abc import ABC, abstractmethod


class AvatarFinderControllerInterface(ABC):

    @abstractmethod
    async def find(self, user_id: int) -> dict:
        pass
