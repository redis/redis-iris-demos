from __future__ import annotations

import redis
import redis.asyncio as redis_asyncio

from backend.app.settings import Settings


def build_redis_url(settings: Settings) -> str:
    """Build a Redis URL from settings."""
    scheme = "rediss" if settings.redis_ssl else "redis"
    auth = ""
    if settings.redis_password:
        user = settings.redis_username or "default"
        auth = f"{user}:{settings.redis_password}@"
    return f"{scheme}://{auth}{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"


def create_redis_client(settings: Settings) -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        username=settings.redis_username or "default",
        password=settings.redis_password or None,
        db=settings.redis_db,
        ssl=settings.redis_ssl,
        decode_responses=True,
        socket_connect_timeout=10,
        socket_timeout=10,
        max_connections=settings.redis_max_connections,
        health_check_interval=30,
    )


def create_async_redis_client(settings: Settings) -> redis_asyncio.Redis:
    return redis_asyncio.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        username=settings.redis_username or "default",
        password=settings.redis_password or None,
        db=settings.redis_db,
        ssl=settings.redis_ssl,
        decode_responses=True,
        socket_connect_timeout=10,
        socket_timeout=10,
        max_connections=settings.redis_max_connections,
        health_check_interval=30,
    )
