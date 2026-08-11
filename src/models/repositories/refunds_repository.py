# pylint: disable=w0212
from datetime import datetime
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

    async def available_years(self, user_id: Optional[int]) -> list[int]:
        """The years that actually have refunds, oldest first.

        Exists so the year picker offers only years that could show something. The
        alternative — the client guessing "this year and the four before" — would
        offer years that are empty by construction, and an empty chart the user was
        invited to open is worse than a year not offered.
        """
        async with self.__db_connection.connect() as session:
            year = func.extract("year", Refunds.c.created_at)  # pylint: disable=not-callable
            query = select(year).select_from(Refunds).group_by(year).order_by(year.asc())
            if user_id is not None:
                query = query.where(Refunds.c.user_id == user_id)
            return [int(row[0]) for row in (await session.execute(query)).fetchall()]

    async def summarize_refunds(
        self, user_id: Optional[int], since: datetime, until: datetime
    ) -> tuple[dict, dict, list]:
        """Three independent aggregations over the same filtered set.

        Three queries and not one: grouping by status AND category AND month in a
        single statement would return the cross product of all three, and the
        caller would have to re-aggregate it twice to get the totals it wanted.

        The window and the user filter are in EVERY one of them. A status total
        that ignored the window would disagree with the months that are supposed
        to add up to it.

        The window is half-open, [since, until): a closed upper bound would need to
        name the last instant of the year, and "23:59:59" silently drops whatever
        happens in the final second.
        """
        async with self.__db_connection.connect() as session:
            filters = [Refunds.c.created_at >= since, Refunds.c.created_at < until]
            if user_id is not None:
                filters.append(Refunds.c.user_id == user_id)

            by_status = self.__grouped(
                await session.execute(self.__group_query(Refunds.c.status, filters))
            )
            by_category = self.__grouped(
                await session.execute(self.__group_query(Refunds.c.category, filters))
            )

            # The month rows carry status as a second key. That cross-tab is what
            # feeds the stacked chart, and asking for it separately would be a
            # fourth scan of the same rows.
            month = func.date_trunc("month", Refunds.c.created_at)
            month_query = (
                select(
                    month,
                    Refunds.c.status,
                    func.count(),  # pylint: disable=not-callable
                    func.sum(Refunds.c.amount_in_cents),
                )
                .select_from(Refunds)
                .where(*filters)
                .group_by(month, Refunds.c.status)
                .order_by(month.asc())
            )
            by_month = [
                {
                    "month": row[0].strftime("%Y-%m"),
                    "status": row[1],
                    "count": row[2],
                    "amount_in_cents": row[3] or 0,
                }
                for row in (await session.execute(month_query)).fetchall()
            ]

            return by_status, by_category, by_month

    def __group_query(self, column, filters):
        return (
            select(
                column,
                func.count(),  # pylint: disable=not-callable
                func.sum(Refunds.c.amount_in_cents),
            )
            .select_from(Refunds)
            .where(*filters)
            .group_by(column)
        )

    def __grouped(self, result) -> dict:
        # `or 0` guards the NULL an all-NULL column would produce — the same guard
        # count_by_status carries. Only the keys the database returned are here;
        # filling the missing ones with zeros is the controller's job, because the
        # canonical key lists are a contract decision, not a storage one.
        return {
            key: {"count": count, "amount_in_cents": total or 0}
            for key, count, total in result.fetchall()
        }

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
            "payment_filename": data["payment_filename"],
            "status": data["status"],
            "created_at": data["created_at"],
            "user": {
                "id": data["user_id"],
                "name": data["user_name"],
                "avatar_filename": data["avatar_filename"],
            },
        }

    async def count_by_status(self, user_id: int) -> dict:
        async with self.__db_connection.connect() as session:
            # One round trip for every status. SUM over an empty group cannot
            # happen here (a group only exists if it has rows), but `or 0`
            # guards the NULL that a all-NULL column would produce.
            query = (
                select(
                    Refunds.c.status,
                    func.count(),  # pylint: disable=not-callable
                    func.sum(Refunds.c.amount_in_cents),
                )
                .select_from(Refunds)
                .where(Refunds.c.user_id == user_id)
                .group_by(Refunds.c.status)
            )
            rows = (await session.execute(query)).fetchall()

            return {
                status: {"count": count, "amount_in_cents": amount or 0}
                for status, count, amount in rows
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
