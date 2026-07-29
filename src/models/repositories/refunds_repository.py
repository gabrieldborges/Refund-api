# pylint: disable=w0212
from typing import Optional
from sqlalchemy import insert, select, delete, func
from src.models.entities.refunds import Refunds
from src.models.settings.database_connection_handler import DatabaseConnectionHandler
from .interfaces.refunds_repository_interface import RefundsRepositoryInterface


class RefundsRepository(RefundsRepositoryInterface):
    def __init__(self, database_connection: DatabaseConnectionHandler) -> None:
        self.__db_connection = database_connection

    async def insert_refund(self, refund_info: dict) -> int:
        async with self.__db_connection.connect() as session:
            query = insert(Refunds).values(**refund_info)
            result = await session.execute(query)
            await session.commit()
            return result.inserted_primary_key[0]

    async def select_refunds(
        self,
        page: int,
        per_page: int,
        name: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> tuple[list[dict], int, int]:
        async with self.__db_connection.connect() as session:
            filters = []
            if user_id is not None:
                filters.append(Refunds.c.user_id == user_id)
            if name:
                filters.append(Refunds.c.name.ilike(f"%{name}%"))

            # count and sum share the same filters, so they ride in one query
            # instead of two round trips. SUM over an empty set returns NULL,
            # hence the `or 0`.
            totals_query = (
                select(func.count(), func.sum(Refunds.c.amount_in_cents))  # pylint: disable=not-callable
                .select_from(Refunds)
                .where(*filters)
            )
            total, total_amount = (await session.execute(totals_query)).one()

            query = (
                select(Refunds)
                .where(*filters)
                .order_by(Refunds.c.created_at.desc())
                .limit(per_page)
                .offset((page - 1) * per_page)
            )
            result = await session.execute(query)
            rows = result.fetchall()

            refunds = [dict(row._mapping) for row in rows]
            return refunds, total, total_amount or 0

    async def select_refund_by_id(self, refund_id: int) -> Optional[dict]:
        async with self.__db_connection.connect() as session:
            query = select(Refunds).where(Refunds.c.id == refund_id)
            result = await session.execute(query)
            refund = result.fetchone()
            return dict(refund._mapping) if refund else None

    async def delete_refund(self, refund_id: int) -> int:
        async with self.__db_connection.connect() as session:
            # The status filter closes the race with a concurrent review: this
            # delete only touches the row if it is still "pending" at the moment
            # the DELETE runs, instead of trusting a status read by the caller
            # moments earlier in a separate session/transaction. rowcount tells
            # the controller whether a row was actually removed, so it can tell
            # "deleted" apart from "no longer eligible" without a second read.
            query = delete(Refunds).where(Refunds.c.id == refund_id, Refunds.c.status == "pending")
            result = await session.execute(query)
            await session.commit()
            return result.rowcount
