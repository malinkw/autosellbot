"""Служба уведомлений: доставка сообщений пользователям и сотрудникам."""

from __future__ import annotations

from collections.abc import Iterable

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from app.logging import get_logger
from app.models import User

log = get_logger("bot")


class NotificationService:
    """Отправка уведомлений через Telegram с безопасной обработкой ошибок."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send(self, telegram_id: int, text: str) -> bool:
        """Отправить сообщение пользователю. Ошибки не пробрасываются."""
        try:
            await self._bot.send_message(telegram_id, text)
            return True
        except TelegramAPIError as exc:  # пользователь заблокировал бота и т.п.
            log.warning("notify_failed", telegram_id=telegram_id, error=str(exc))
            return False

    async def notify_user(self, user: User, text: str) -> bool:
        """Уведомить пользователя (по модели)."""
        return await self.send(user.telegram_id, text)

    async def broadcast(self, users: Iterable[User], text: str) -> int:
        """Разослать уведомление списку пользователей. Возвращает число доставленных."""
        delivered = 0
        for user in users:
            if await self.send(user.telegram_id, text):
                delivered += 1
        return delivered
