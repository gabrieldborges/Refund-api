from abc import ABC, abstractmethod
from typing import Optional


class RefundReviewsRepositoryInterface(ABC):

    @abstractmethod
    async def insert_review(
        self,
        refund_id: int,
        reviewer_id: int,
        from_status: str,
        to_status: str,
        reason: Optional[str],
    ) -> None:
        pass
