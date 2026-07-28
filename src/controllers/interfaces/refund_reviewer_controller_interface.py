from abc import ABC, abstractmethod
from typing import Optional


class RefundReviewerControllerInterface(ABC):

    @abstractmethod
    async def review(
        self,
        refund_id: int,
        reviewer_id: int,
        role: str,
        status: str,
        reason: Optional[str],
    ) -> dict:
        pass
