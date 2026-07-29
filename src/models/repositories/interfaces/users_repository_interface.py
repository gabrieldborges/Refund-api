from abc import ABC, abstractmethod
from typing import Optional


class UsersRepositoryInterface(ABC):

    @abstractmethod
    async def insert_user(self, user_info: dict) -> int:
        pass

    @abstractmethod
    async def select_user_by_email(self, email: str) -> Optional[dict]:
        pass

    @abstractmethod
    async def select_user_by_id(self, user_id: int) -> Optional[dict]:
        pass

    @abstractmethod
    async def update_avatar(self, user_id: int, avatar_filename: Optional[str]) -> None:
        pass
