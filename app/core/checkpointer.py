"""
Configurable checkpoint system for LangGraph.
Supports: memory (dev), redis (prod), postgres (alternative)
This is CORE INFRASTRUCTURE - Do not modify.
"""

import structlog
from typing import Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.core.config import settings

logger = structlog.get_logger()


def get_checkpointer() -> BaseCheckpointSaver:
    """
    Get configured checkpointer based on CHECKPOINT_BACKEND setting.

    Returns:
        BaseCheckpointSaver: Configured checkpointer instance

    Raises:
        ValueError: If checkpoint backend is invalid
    """
    backend = settings.CHECKPOINT_BACKEND

    if backend == "memory":
        logger.info("Using in-memory checkpointing (development mode)")
        return MemorySaver()

    elif backend == "redis":
        logger.info("Using Redis checkpointing", host=settings.REDIS_HOST)
        try:
            from langgraph.checkpoint.redis import RedisSaver
            import redis

            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=False,
            )

            # Test connection
            redis_client.ping()

            return RedisSaver(redis_client)
        except ImportError:
            logger.error("Redis checkpointing requires: pip install langgraph[redis]")
            raise ValueError("Redis checkpointing not available")
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise ValueError(f"Redis connection failed: {str(e)}")

    elif backend == "postgres":
        logger.info("Using Postgres checkpointing")
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            # Note: Requires POSTGRES_CHECKPOINT_URL in settings
            connection_string = getattr(settings, "POSTGRES_CHECKPOINT_URL", None)
            if not connection_string:
                raise ValueError("POSTGRES_CHECKPOINT_URL not configured")

            return PostgresSaver(connection_string)
        except ImportError:
            logger.error("Postgres checkpointing requires: pip install langgraph[postgres]")
            raise ValueError("Postgres checkpointing not available")
        except Exception as e:
            logger.error("Failed to initialize Postgres checkpointer", error=str(e))
            raise ValueError(f"Postgres checkpointing failed: {str(e)}")

    else:
        raise ValueError(
            f"Invalid CHECKPOINT_BACKEND: {backend}. "
            f"Must be: memory, redis, or postgres"
        )


# Global checkpointer instance
checkpointer = get_checkpointer()
