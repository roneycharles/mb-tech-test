import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from contextlib import asynccontextmanager

from core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DB_URL,
    future=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()

async def init_db() -> None:
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Failed to initialize database", exc_info=e)
        raise

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error("Database session error: %s", e)
            await session.rollback()
            raise

@asynccontextmanager
async def async_session_context():
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.error("Database session error: %s", e)
        await session.rollback()
        raise
    finally:
        await session.close()