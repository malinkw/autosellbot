"""Репозиторий настроек бота."""

from __future__ import annotations

from app.models import BotSetting
from app.repositories.base import BaseRepository


class SettingsRepository(BaseRepository[BotSetting]):
    """Доступ к настройкам бота (key-value)."""

    model = BotSetting

    async def get_by_key(self, key: str) -> BotSetting | None:
        """Найти настройку по ключу."""
        return await self.get_by(key=key)

    async def all_settings(self) -> list[BotSetting]:
        """Все настройки."""
        return await self.list(order_by=[BotSetting.key])
