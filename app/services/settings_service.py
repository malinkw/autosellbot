"""Служба настроек бота (редактируемых из админ-панели)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models import BotSetting
from app.repositories.settings import SettingsRepository


class SettingsService:
    """Чтение и изменение настроек бота."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = SettingsRepository(session)

    async def all(self) -> list[BotSetting]:
        """Все настройки."""
        return await self._repo.all_settings()

    async def get(self, key: str, default: Any = None) -> Any:
        """Получить значение настройки по ключу."""
        setting = await self._repo.get_by_key(key)
        return setting.value if setting is not None else default

    async def set(self, key: str, value: Any) -> BotSetting:
        """Установить значение существующей настройки."""
        setting = await self._repo.get_by_key(key)
        if setting is None:
            raise NotFoundError(f"Настройка «{key}» не найдена.")
        setting.value = value
        await self._session.flush()
        return setting

    async def is_maintenance(self) -> bool:
        """Включён ли режим обслуживания."""
        return bool(await self.get("maintenance_mode", False))

    async def toggle_maintenance(self) -> bool:
        """Переключить режим обслуживания и вернуть новое значение."""
        new_value = not await self.is_maintenance()
        await self.set("maintenance_mode", new_value)
        return new_value
