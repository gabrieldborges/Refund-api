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
    ) -> tuple[list[dict], int]:
        async with self.__db_connection.connect() as session:
            filters = []
            if user_id is not None:
                filters.append(Refunds.c.user_id == user_id)
            if name:
                filters.append(Refunds.c.name.ilike(f"%{name}%"))

            count_query = select(func.count()).select_from(Refunds).where(*filters)  # pylint: disable=not-callable
            total = await session.scalar(count_query)

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
            return refunds, total

    async def select_refund_by_id(self, refund_id: int) -> Optional[dict]:
        async with self.__db_connection.connect() as session:
            query = select(Refunds).where(Refunds.c.id == refund_id)
            result = await session.execute(query)
            refund = result.fetchone()
            return dict(refund._mapping) if refund else None

    async def delete_refund(self, refund_id: int) -> None:
        async with self.__db_connection.connect() as session:
            query = delete(Refunds).where(Refunds.c.id == refund_id)
            await session.execute(query)
            await session.commit()
