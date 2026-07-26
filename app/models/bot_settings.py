"""Модель настроек бота (key-value), редактируемых из админ-панели."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin


class BotSetting(Base, UUIDMixin, TimestampMixin):
    """Одна настройка приложения (значение хранится как JSON)."""

    __tablename__ = "bot_settings"

    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(128))
    value: Mapped[Any] = mapped_column(JSON, default=None)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<BotSetting {self.key}={self.value!r}>"
