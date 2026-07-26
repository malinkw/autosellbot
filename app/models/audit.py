"""Модель аудита: неизменяемый журнал всех значимых действий."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDMixin


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Запись аудита.

    Содержит все требуемые ТЗ поля: дату/время (``created_at``), пользователя и
    сотрудника, IP (если доступен), действие, старые и новые данные, результат.
    """

    __tablename__ = "audit_logs"

    channel: Mapped[str] = mapped_column(String(16), default="bot", index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None, index=True
    )
    actor_telegram_id: Mapped[int | None] = mapped_column(default=None, index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
    ip: Mapped[str | None] = mapped_column(String(64), default=None)
    old_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    new_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    result: Mapped[str] = mapped_column(String(16), default="success")
    message: Mapped[str | None] = mapped_column(Text, default=None)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog {self.action} result={self.result}>"
