# pylint: disable=w0212
from typing import Optional
from sqlalchemy import insert, select, update
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

    async def update_avatar(self, user_id: int, avatar_filename: Optional[str]) -> None:
        async with self.__db_connection.connect() as session:
            query = (
                update(Users)
                .where(Users.c.id == user_id)
                .values(avatar_filename=avatar_filename)
            )
            await session.execute(query)
            await session.commit()
