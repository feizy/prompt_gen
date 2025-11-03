"""
Redis client configuration
"""

import aioredis
from typing import Optional

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection"""
    global redis_client

    logger.info("Initializing Redis connection")

    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )

    # Test connection
    await redis_client.ping()
    logger.info("Redis connection initialized")


async def get_redis() -> aioredis.Redis:
    """Get Redis client"""
    if not redis_client:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return redis_client


async def close_redis() -> None:
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")