"""Middleware аутентификации: upsert пользователя, блокировки, режим обслуживания."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram.types import User as TgUser

from app.models.enums import AccountStatus
from app.services import ServiceContainer


class AuthMiddleware(BaseMiddleware):
    """Гарантирует наличие профиля пользователя и применяет ограничения доступа."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        services: ServiceContainer = data["services"]
        user, created = await services.users.get_or_create(
            tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
        )
        data["user"] = user
        data["created"] = created

        # Блокировка аккаунта.
        if user.status is AccountStatus.BLOCKED:
            await self._reply(event, "⛔ Ваш аккаунт заблокирован.")
            return None

        # Режим обслуживания (владельцы и админы работают всегда).
        if await services.bot_settings.is_maintenance() and not services.permissions.is_admin(user):
            await self._reply(event, "🛠 Бот на техническом обслуживании. Загляните позже.")
            return None

        return await handler(event, data)

    @staticmethod
    async def _reply(event: TelegramObject, text: str) -> None:
        if isinstance(event, Message):
            await event.answer(text)
        elif isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
