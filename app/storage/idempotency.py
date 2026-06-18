from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

import redis.asyncio as redis


class IdempotencyStore(ABC):
    @abstractmethod
    async def mark_once(self, key: str, ttl_seconds: int = 3600) -> bool:
        raise NotImplementedError


class InMemoryIdempotencyStore(IdempotencyStore):
    def __init__(self):
        self._seen: dict[str, datetime] = {}

    async def mark_once(self, key: str, ttl_seconds: int = 3600) -> bool:
        now = datetime.now(timezone.utc)
        self._seen = {k: v for k, v in self._seen.items() if v > now}
        if key in self._seen:
            return False
        self._seen[key] = now + timedelta(seconds=ttl_seconds)
        return True


class RedisIdempotencyStore(IdempotencyStore):
    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url, decode_responses=True)

    async def mark_once(self, key: str, ttl_seconds: int = 3600) -> bool:
        result = await self.client.set(name=f"idempotency:{key}", value="1", ex=ttl_seconds, nx=True)
        return bool(result)

