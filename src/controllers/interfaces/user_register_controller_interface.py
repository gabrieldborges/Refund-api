from abc import ABC, abstractmethod


class UserRegisterControllerInterface(ABC):

    @abstractmethod
    async def register(self, user_data: dict) -> dict:
        pass
