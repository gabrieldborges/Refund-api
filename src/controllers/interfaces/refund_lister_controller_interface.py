from abc import ABC, abstractmethod
from datetime import date
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
        filter_user_id: Optional[int] = None,
        created_from: Optional[date] = None,
        created_to: Optional[date] = None,
    ) -> dict:
        pass
