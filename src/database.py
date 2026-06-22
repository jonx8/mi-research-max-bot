import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.asyncio.session import AsyncSession

from src.models import Base

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url, future=True)
        self.AsyncSessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def init_db(self) -> None:
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Контекстный менеджер для async сессии"""
        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Ошибка базы данных: {e}", exc_info=True)
                raise
            finally:
                await session.close()
