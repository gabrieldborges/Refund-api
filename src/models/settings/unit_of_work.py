from typing import Optional
from src.models.repositories.refund_status_repository import RefundStatusRepository
from src.models.repositories.refund_reviews_repository import RefundReviewsRepository
from .database_connection_handler import DatabaseConnectionHandler


class UnitOfWork:
    # Delimits ONE transaction for ONE use case, and hands out repositories bound
    # to it. Repositories that take a session (instead of opening their own) can
    # therefore write inside the same transaction and land together.
    #
    # This is deliberately NOT used by the existing single-write CRUDs: with one
    # write there is nothing to coordinate, and wrapping them would add
    # indirection without buying a guarantee.
    def __init__(self, database_connection: DatabaseConnectionHandler) -> None:
        self.__db_connection = database_connection
        self.__session_ctx = None
        self.__session = None
        self.refunds: Optional[RefundStatusRepository] = None
        self.reviews: Optional[RefundReviewsRepository] = None

    async def __aenter__(self) -> "UnitOfWork":
        self.__session_ctx = self.__db_connection.connect()
        self.__session = await self.__session_ctx.__aenter__()
        self.refunds = RefundStatusRepository(self.__session)
        self.reviews = RefundReviewsRepository(self.__session)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        # Rolling back on the way out is what makes an exception anywhere in the
        # block safe: no caller needs a try/except to undo a partial write.
        # The rollback itself can fail (the original exception may already have
        # broken the DBAPI connection), so it is wrapped in try/finally: closing
        # the session must not depend on the rollback succeeding, or a failed
        # rollback would leak the connection and starve the pool.
        try:
            if exc_type is not None:
                await self.__session.rollback()
        finally:
            await self.__session_ctx.__aexit__(exc_type, exc_value, traceback)

    async def commit(self) -> None:
        await self.__session.commit()
