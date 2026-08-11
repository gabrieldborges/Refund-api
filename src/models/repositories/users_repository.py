# pylint: disable=w0212
from typing import Optional
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError
from src.models.entities.users import Users
from src.models.settings.database_connection_handler import DatabaseConnectionHandler
from src.errors.types.http_bad_request_error import HttpBadRequestError
from .interfaces.users_repository_interface import UsersRepositoryInterface


class UsersRepository(UsersRepositoryInterface):
    def __init__(self, database_connection: DatabaseConnectionHandler) -> None:
        self.__db_connection = database_connection

    async def insert_user(self, user_info: dict) -> int:
        async with self.__db_connection.connect() as session:
            query = insert(Users).values(**user_info)
            try:
                result = await session.execute(query)
                await session.commit()
                return result.inserted_primary_key[0]
            except IntegrityError as exception:
                await session.rollback()
                raise HttpBadRequestError("Email already registered") from exception

    async def select_user_by_email(self, email: str) -> dict:
        async with self.__db_connection.connect() as session:
            query = select(Users).where(Users.c.email == email)
            result = await session.execute(query)
            user = result.fetchone()
            return dict(user._mapping) if user else None

    async def select_user_by_id(self, user_id: int) -> dict:
        async with self.__db_connection.connect() as session:
            query = select(Users).where(Users.c.id == user_id)
            result = await session.execute(query)
            user = result.fetchone()
            return dict(user._mapping) if user else None

    async def select_users(
        self, page: int, per_page: int, name: Optional[str] = None
    ) -> tuple[list[dict], int]:
        async with self.__db_connection.connect() as session:
            filters = []
            # `if name` and not `if name is not None`: an empty string would
            # become LIKE '%%', which reads as a filter in the SQL while
            # matching everything.
            if name:
                filters.append(Users.c.name.ilike(f"%{name}%"))

            # Counted with the SAME filters as the page. A total that ignored
            # them would make total_pages promise pages the page query can
            # never fill.
            total_query = (
                select(func.count())  # pylint: disable=not-callable
                .select_from(Users)
                .where(*filters)
            )
            total = (await session.execute(total_query)).scalar_one()

            query = (
                select(Users)
                .where(*filters)
                # Tiebreaker on id for the same reason as
                # RefundsRepository.__order_by: PostgreSQL guarantees no
                # ordering among rows whose sort key is equal, so with
                # LIMIT/OFFSET a tie can put one row on two pages while
                # another never appears at all. Namesakes are ordinary, which
                # makes this tie the norm here rather than an edge case.
                .order_by(Users.c.name.asc(), Users.c.id.asc())
                .limit(per_page)
                .offset((page - 1) * per_page)
            )
            rows = (await session.execute(query)).fetchall()

            # The whole row, hash included. Keeping `password` out of responses
            # is user_serializer's job, not this layer's: a repository that
            # decided what is public would have to be consulted every time a
            # new use case needed a different subset.
            return [dict(row._mapping) for row in rows], total

    async def update_avatar(self, user_id: int, avatar_filename: Optional[str]) -> None:
        async with self.__db_connection.connect() as session:
            query = (
                update(Users)
                .where(Users.c.id == user_id)
                .values(avatar_filename=avatar_filename)
            )
            await session.execute(query)
            await session.commit()
