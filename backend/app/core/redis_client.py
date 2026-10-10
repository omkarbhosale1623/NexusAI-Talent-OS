"""redis_client.py — shared async Redis connection"""
import redis.asyncio as aioredis
from app.core.config import settings

redis_client = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=False,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    socket_timeout=5,
    socket_connect_timeout=5,
)
