"""Провайдер подключения к Redis (FSM-хранилище, throttling, кэш, идемпотентность)."""

from __future__ import annotations

from redis.asyncio import Redis, from_url

from app.config import Settings


class RedisProvider:
    """Ленивая обёртка над асинхронным клиентом Redis."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Redis | None = None

    @property
    def client(self) -> Redis:
        """Вернуть (создав при необходимости) клиент Redis."""
        if self._client is None:
            self._client = from_url(
                self._settings.redis.dsn,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def ping(self) -> bool:
        """Проверить доступность Redis."""
        return bool(await self.client.ping())

    async def close(self) -> None:
        """Закрыть соединение."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
