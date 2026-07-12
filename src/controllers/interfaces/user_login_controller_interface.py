from abc import ABC, abstractmethod


class UserLoginControllerInterface(ABC):

    @abstractmethod
    async def login(self, credentials: dict) -> dict:
        pass
