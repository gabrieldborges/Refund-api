from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.configs.global_config import database_info


CONNECTION_STRING = str(database_info["DATABASE_URL"])


engine = create_async_engine(
    CONNECTION_STRING,
    echo=False,
    # Was pool_size=2, max_overflow=0: a ceiling of TWO concurrent operations
    # for the whole process. The review flow takes a row lock inside a
    # transaction, so two blocked reviewers used to exhaust the pool and a
    # third request — even a login — waited pool_timeout and got a 500.
    pool_size=5,
    max_overflow=10,
    # Lowered from 30s: with a ceiling of 15, waiting half a minute for a
    # connection means something is badly wrong and the browser gave up long
    # ago. Failing at 10s produces a legible error instead of a hung request.
    pool_timeout=10,
    # The DATABASE_URL points at a DIRECT Neon endpoint (no "-pooler"), which
    # suspends idle compute and closes connections. Without pre-ping the pool
    # hands out a connection the server already dropped.
    pool_pre_ping=True,
    pool_recycle=300,
    # Closes the other half of the pool pendency: select_for_update in the
    # review flow used to wait indefinitely while holding a connection. This is
    # GLOBAL — every statement, not just that one — which is acceptable because
    # that is the only place in the system that takes a lock. The surgical
    # alternative would be SET LOCAL lock_timeout inside UnitOfWork.
    #
    # Delivered through `options` rather than as a server_settings key of its
    # own, which is what asyncpg's docs suggest and what this plan first
    # specified. Against this Neon endpoint that silently does nothing: the
    # proxy forwards startup parameters it "reports" (application_name arrives
    # fine) and drops the rest, so SHOW lock_timeout answered 0 with no error
    # anywhere. `options` is passed through as a single opaque string and
    # survives. Verified with SHOW lock_timeout.
    connect_args={"server_settings": {"options": "-c lock_timeout=3000"}},
)

async_session = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

class DatabaseConnectionHandler:
    # connect() opens a NEW session per call and keeps it in a local variable —
    # never on self. That is what makes a single shared handler safe under
    # concurrency: two overlapping requests each get their own session instead of
    # overwriting a shared one. The engine/sessionmaker above stay module-level
    # (correctly shared); only the per-operation session is scoped locally.
    @asynccontextmanager
    async def connect(self):
        session: AsyncSession = async_session()
        try:
            yield session
        finally:
            await session.close()


database_connection_handler = DatabaseConnectionHandler()
