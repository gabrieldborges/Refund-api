from typing import Optional
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.entities.refund_reviews import RefundReviews
from src.models.entities.users import Users
from .interfaces.refund_reviews_repository_interface import RefundReviewsRepositoryInterface
from .interfaces.refund_reviews_reader_repository_interface import (
    RefundReviewsReaderRepositoryInterface,
)


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


class RefundReviewsReaderRepository(RefundReviewsReaderRepositoryInterface):
    # Sibling of RefundReviewsRepository above, split by transaction ownership
    # rather than by table: that one is session-injected because the UnitOfWork
    # drives its writes, this one opens its own session because a standalone
    # read has no transaction to join. Same split as
    # RefundStatusRepository (injected) vs RefundsRepository (own session).
    def __init__(self, db_connection) -> None:
        self.__db_connection = db_connection

    async def select_by_refund_id(self, refund_id: int) -> list[dict]:
        async with self.__db_connection.connect() as session:
            # Joins Users because the timeline shows WHO decided, and the
            # reviewer's name is not on refund_reviews.
            query = (
                select(
                    RefundReviews.c.from_status,
                    RefundReviews.c.to_status,
                    RefundReviews.c.reason,
                    RefundReviews.c.created_at,
                    Users.c.id.label("reviewer_id"),
                    Users.c.name.label("reviewer_name"),
                )
                .select_from(
                    RefundReviews.join(Users, RefundReviews.c.reviewer_id == Users.c.id)
                )
                # Chronological, with id as the tie-breaker: two decisions can
                # share a created_at, and a timeline that reorders itself
                # between requests is worse than one that is merely coarse.
                .order_by(RefundReviews.c.created_at.asc(), RefundReviews.c.id.asc())
                .where(RefundReviews.c.refund_id == refund_id)
            )
            rows = (await session.execute(query)).fetchall()
            return [dict(row._mapping) for row in rows]  # pylint: disable=protected-access
