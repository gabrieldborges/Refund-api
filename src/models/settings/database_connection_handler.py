from typing import Optional
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
    def __init__(self) -> None:
        self.session: Optional[AsyncSession] = None

    async def __aenter__(self):
        self.session = async_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()


database_connection_handler = DatabaseConnectionHandler()
