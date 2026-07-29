# pylint: disable=w0212
from typing import Optional
from sqlalchemy import insert, select, delete, func
from src.models.entities.refunds import Refunds
from src.models.entities.users import Users
from src.models.settings.database_connection_handler import DatabaseConnectionHandler
from .interfaces.refunds_repository_interface import RefundsRepositoryInterface


# The sort name from the client is a KEY into this dictionary, never text placed
# into SQL. An unknown name cannot produce a column at all — it falls back to the
# default — so no string from a request can ever reach the ORDER BY.
SORTABLE_COLUMNS = {
    "created_at": Refunds.c.created_at,
    "amount_in_cents": Refunds.c.amount_in_cents,
    "name": Refunds.c.name,
    "status": Refunds.c.status,
}


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
        status: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ) -> tuple[list[dict], int, int]:
        async with self.__db_connection.connect() as session:
            filters = []
            if user_id is not None:
                filters.append(Refunds.c.user_id == user_id)
            if name:
                filters.append(Refunds.c.name.ilike(f"%{name}%"))
            if status:
                filters.append(Refunds.c.status == status)

            # count and sum share the same filters, so they ride in one query
            # instead of two round trips. SUM over an empty set returns NULL,
            # hence the `or 0`. No join here: neither aggregate needs users.
            totals_query = (
                select(func.count(), func.sum(Refunds.c.amount_in_cents))  # pylint: disable=not-callable
                .select_from(Refunds)
                .where(*filters)
            )
            total, total_amount = (await session.execute(totals_query)).one()

            query = (
                select(
                    Refunds,
                    # Labelled because Refunds also has a "name" column; without
                    # the label the two would collide in the row mapping.
                    Users.c.name.label("user_name"),
                    Users.c.avatar_filename,
                )
                .select_from(Refunds.join(Users, Refunds.c.user_id == Users.c.id))
                .where(*filters)
                .order_by(*self.__order_by(sort, order))
                .limit(per_page)
                .offset((page - 1) * per_page)
            )
            rows = (await session.execute(query)).fetchall()

            return [self.__to_refund(row) for row in rows], total, total_amount or 0

    async def select_refund_by_id(self, refund_id: int) -> Optional[dict]:
        async with self.__db_connection.connect() as session:
            query = (
                select(
                    Refunds,
                    Users.c.name.label("user_name"),
                    Users.c.avatar_filename,
                )
                .select_from(Refunds.join(Users, Refunds.c.user_id == Users.c.id))
                .where(Refunds.c.id == refund_id)
            )
            refund = (await session.execute(query)).fetchone()
            return self.__to_refund(refund) if refund else None

    def __order_by(self, sort: Optional[str], order: Optional[str]):
        column = SORTABLE_COLUMNS.get(sort or "created_at", Refunds.c.created_at)
        primary = column.asc() if order == "asc" else column.desc()
        # Tiebreaker: PostgreSQL guarantees no ordering among rows whose primary
        # sort key is equal, so with LIMIT/OFFSET a tie can put the same row on
        # two different pages while another row never appears at all. This is
        # rare with created_at but the norm with status/name/amount_in_cents
        # (e.g. every "pending" refund ties under sort=status). Appending id
        # DESC as a secondary key makes the ordering total, so pagination is
        # deterministic regardless of how many rows share the primary key.
        return primary, Refunds.c.id.desc()

    def __to_refund(self, row) -> dict:
        data = dict(row._mapping)
        return {
            "id": data["id"],
            "name": data["name"],
            "category": data["category"],
            "amount_in_cents": data["amount_in_cents"],
            "filename": data["filename"],
            "status": data["status"],
            "created_at": data["created_at"],
            "user": {
                "id": data["user_id"],
                "name": data["user_name"],
                "avatar_filename": data["avatar_filename"],
            },
        }

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
