from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.configs.global_config import database_info


CONNECTION_STRING = str(database_info["DATABASE_URL"])


engine = create_async_engine(
    CONNECTION_STRING,
    echo=False,
    pool_size=2,
    max_overflow=0,
    pool_timeout=30
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
