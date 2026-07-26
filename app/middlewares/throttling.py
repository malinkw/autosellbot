"""Middleware троттлинга (Rate Limit / защита от Flood) на базе Redis."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as TgUser
from redis.asyncio import Redis


class ThrottlingMiddleware(BaseMiddleware):
    """Ограничивает частоту запросов от одного пользователя.

    Использует скользящий счётчик в Redis: не более ``rate`` действий за 1 секунду.
    """

    def __init__(self, redis: Redis, *, rate: int = 3) -> None:
        self._redis = redis
        self._rate = rate

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        key = f"throttle:{tg_user.id}"
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, 1)
        if count > self._rate:
            if isinstance(event, CallbackQuery):
                await event.answer("Слишком часто. Подождите секунду.", show_alert=False)
            elif isinstance(event, Message):
                await event.answer("⏳ Слишком много запросов, подождите секунду.")
            return None

        return await handler(event, data)
