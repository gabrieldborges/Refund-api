from abc import ABC, abstractmethod
from typing import Optional


class RefundSummaryControllerInterface(ABC):

    @abstractmethod
    async def summarize(
        self,
        user_id: int,
        role: str,
        months: int,
        filter_user_id: Optional[int] = None,
    ) -> dict:
        pass
