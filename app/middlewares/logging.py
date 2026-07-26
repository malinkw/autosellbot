"""Middleware логирования: привязка контекста апдейта к structlog."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from aiogram.types import User as TgUser


class LoggingMiddleware(BaseMiddleware):
    """Добавляет в контекст логов идентификаторы апдейта и пользователя."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        structlog.contextvars.clear_contextvars()
        bindings: dict[str, Any] = {}
        if isinstance(event, Update):
            bindings["update_id"] = event.update_id
        if tg_user is not None:
            bindings["telegram_id"] = tg_user.id
        structlog.contextvars.bind_contextvars(**bindings)
        try:
            return await handler(event, data)
        finally:
            structlog.contextvars.clear_contextvars()
