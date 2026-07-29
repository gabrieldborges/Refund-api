from abc import ABC, abstractmethod


class AvatarRemoverControllerInterface(ABC):

    @abstractmethod
    async def remove(self, user_id: int) -> dict:
        pass
