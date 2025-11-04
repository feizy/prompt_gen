"""
Redis client configuration
"""

import redis
from typing import Optional

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

redis_client: Optional[redis.Redis] = None


def init_redis() -> None:
    """Initialize Redis connection (optional)"""
    global redis_client

    try:
        logger.info("Initializing Redis connection")

        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )

        # Test connection
        redis_client.ping()
        logger.info("Redis connection initialized")
    except Exception as e:
        logger.warning(f"Redis connection failed, continuing without Redis: {e}")
        redis_client = None


def get_redis() -> redis.Redis:
    """Get Redis client"""
    if not redis_client:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return redis_client


def close_redis() -> None:
    """Close Redis connection"""
    global redis_client
    if redis_client:
        redis_client.close()
        redis_client = None
        logger.info("Redis connection closed")