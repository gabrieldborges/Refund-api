from typing import Optional
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.entities.refund_reviews import RefundReviews
from .interfaces.refund_reviews_repository_interface import RefundReviewsRepositoryInterface


class RefundReviewsRepository(RefundReviewsRepositoryInterface):
    # Session-injected and commit-free, for the same reason as
    # RefundStatusRepository: the UnitOfWork owns the transaction.
    def __init__(self, session: AsyncSession) -> None:
        self.__session = session

    async def insert_review(
        self,
        refund_id: int,
        reviewer_id: int,
        from_status: str,
        to_status: str,
        reason: Optional[str],
    ) -> None:
        query = insert(RefundReviews).values(
            refund_id=refund_id,
            reviewer_id=reviewer_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
        )
        await self.__session.execute(query)
