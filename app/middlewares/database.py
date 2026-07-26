"""Middleware: сессия БД и контейнер сервисов на каждый апдейт."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject
from redis.asyncio import Redis

from app.config import Settings
from app.database import Database
from app.services import ServiceContainer


class DatabaseMiddleware(BaseMiddleware):
    """Открывает транзакционную сессию и кладёт :class:`ServiceContainer` в контекст.

    Сессия коммитится при успешном выполнении хендлера и откатывается при
    исключении (логика в :meth:`Database.session`).
    """

    def __init__(self, database: Database, settings: Settings, redis: Redis, bot: Bot) -> None:
        self._database = database
        self._settings = settings
        self._redis = redis
        self._bot = bot

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self._database.session() as session:
            container = ServiceContainer(session, self._settings, redis=self._redis, bot=self._bot)
            data["services"] = container
            data["session"] = session
            return await handler(event, data)
