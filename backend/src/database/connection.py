"""
Database connection and session management
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

# Database engine and session
engine = None
async_session_maker = None

Base = declarative_base()


async def init_db() -> None:
    """Initialize database connection"""
    global engine, async_session_maker

    logger.info("Initializing database connection")

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    logger.info("Database connection initialized")


async def get_db_session() -> AsyncSession:
    """Get database session"""
    if not async_session_maker:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_async_session():
    """Get database session for FastAPI dependency injection"""
    if not async_session_maker:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async def dependency() -> AsyncSession:
        async with async_session_maker() as session:
            try:
                yield session
            finally:
                await session.close()

    return dependency


async def close_db() -> None:
    """Close database connection"""
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database connection closed")