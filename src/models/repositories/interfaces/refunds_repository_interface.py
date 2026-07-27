from abc import ABC, abstractmethod
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
    ) -> tuple[list[dict], int, int]:
        pass

    @abstractmethod
    async def select_refund_by_id(self, refund_id: int) -> Optional[dict]:
        pass

    @abstractmethod
    async def delete_refund(self, refund_id: int) -> None:
        pass
