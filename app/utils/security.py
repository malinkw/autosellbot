"""Утилиты безопасности: идемпотентность колбэков (защита от Replay-атак)."""

from __future__ import annotations

from redis.asyncio import Redis


class IdempotencyGuard:
    """Однократное выполнение действия по ключу (защита от повторов/двойных нажатий).

    Использует атомарный ``SET key value NX EX ttl`` в Redis: первый вызов
    получает ``True`` и «занимает» ключ на ``ttl`` секунд, повторные — ``False``.
    """

    def __init__(self, redis: Redis, *, namespace: str = "idem") -> None:
        self._redis = redis
        self._ns = namespace

    async def acquire(self, key: str, *, ttl: int = 10) -> bool:
        """Попытаться занять ключ. ``True`` — можно выполнять действие."""
        acquired = await self._redis.set(f"{self._ns}:{key}", "1", nx=True, ex=ttl)
        return bool(acquired)
