# pylint: disable=w0212
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.entities.refunds import Refunds
from .interfaces.refund_status_repository_interface import RefundStatusRepositoryInterface


class RefundStatusRepository(RefundStatusRepositoryInterface):
    # Unlike RefundsRepository, this one neither opens a session nor commits: it
    # receives the session from the UnitOfWork, so its writes join the same
    # transaction as RefundReviewsRepository's and land (or roll back) together.
    def __init__(self, session: AsyncSession) -> None:
        self.__session = session

    async def select_for_update(self, refund_id: int) -> Optional[dict]:
        # Returns the FLAT row shape: top-level "user_id", no nested "user".
        # RefundsRepository.select_refund_by_id also reads the refunds table
        # and is also typed -> Optional[dict], but nests the requester under
        # "user" instead. The two are NOT interchangeable — do not swap one
        # for the other assuming the same shape comes back.
        query = select(Refunds).where(Refunds.c.id == refund_id).with_for_update()
        result = await self.__session.execute(query)
        refund = result.fetchone()
        return dict(refund._mapping) if refund else None

    async def update_status(self, refund_id: int, status: str) -> None:
        query = update(Refunds).where(Refunds.c.id == refund_id).values(status=status)
        await self.__session.execute(query)

    async def mark_as_paid(self, refund_id: int, payment_filename: str) -> int:
        # Conditional on the current status: if a concurrent request already
        # paid this refund, the WHERE matches nothing and rowcount is 0. That
        # closes the race WITHOUT taking a lock, unlike select_for_update above
        # — a lock would hold a pool connection while waiting.
        query = (
            update(Refunds)
            .where(Refunds.c.id == refund_id, Refunds.c.status == "approved")
            .values(status="paid", payment_filename=payment_filename)
        )
        result = await self.__session.execute(query)
        return result.rowcount
