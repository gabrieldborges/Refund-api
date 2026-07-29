from abc import ABC, abstractmethod
from typing import Optional


class RefundListerControllerInterface(ABC):

    @abstractmethod
    async def list(
        self,
        page: int,
        per_page: int,
        user_id: int,
        role: str,
        name: Optional[str] = None,
        status: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ) -> dict:
        pass
