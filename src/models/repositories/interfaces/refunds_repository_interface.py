from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


class RefundsRepositoryInterface(ABC):

    @abstractmethod
    async def insert_refund(self, refund_info: dict) -> int:
        pass

    @abstractmethod
    async def select_refunds(
        self,
        page: int,
        per_page: int,
        name: Optional[str] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ) -> tuple[list[dict], int, int]:
        pass

    @abstractmethod
    async def select_refund_by_id(self, refund_id: int) -> Optional[dict]:
        pass

    @abstractmethod
    async def delete_refund(self, refund_id: int) -> int:
        pass

    @abstractmethod
    async def count_by_status(self, user_id: int) -> dict:
        pass

    @abstractmethod
    async def summarize_refunds(
        self, user_id: Optional[int], since: datetime, until: datetime
    ) -> tuple[dict, dict, list]:
        pass

    @abstractmethod
    async def available_years(self, user_id: Optional[int]) -> list[int]:
        pass
