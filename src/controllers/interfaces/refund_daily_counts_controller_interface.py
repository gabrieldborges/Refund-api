from abc import ABC, abstractmethod
from typing import Optional


class RefundDailyCountsControllerInterface(ABC):

    @abstractmethod
    async def count(
        self,
        user_id: int,
        role: str,
        year: int,
        month: int,
        filter_user_id: Optional[int] = None,
    ) -> dict:
        pass
