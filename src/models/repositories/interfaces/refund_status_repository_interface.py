from abc import ABC, abstractmethod
from typing import Optional


class RefundStatusRepositoryInterface(ABC):

    @abstractmethod
    async def select_for_update(self, refund_id: int) -> Optional[dict]:
        pass

    @abstractmethod
    async def update_status(self, refund_id: int, status: str) -> None:
        pass

    @abstractmethod
    async def mark_as_paid(self, refund_id: int, payment_filename: str) -> int:
        pass
