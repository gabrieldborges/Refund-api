# pylint: disable=duplicate-code
# duplicate-code: R0801 started flagging this file against
# refunds_repository_interface once select_users made it long enough. What the
# two share is the @abstractmethod / async def / pass rhythm that declaring an
# ABC requires — the shape belongs to the language, not to us, and the method
# names and signatures have nothing in common. Same disable, for the same
# reason, as main/routes/user_routes.py.
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
    async def select_users(
        self, page: int, per_page: int, name: Optional[str] = None
    ) -> tuple[list[dict], int]:
        pass

    @abstractmethod
    async def update_avatar(self, user_id: int, avatar_filename: Optional[str]) -> None:
        pass
