from abc import ABC, abstractmethod
from typing import Optional


class UserListerControllerInterface(ABC):

    @abstractmethod
    async def list(
        self, page: int, per_page: int, role: str, name: Optional[str] = None
    ) -> dict:
        pass
