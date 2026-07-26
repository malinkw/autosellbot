"""Декларативная база и общие миксины моделей.

Все доменные таблицы наследуют :class:`Base` и получают:

* ``id``         — первичный ключ UUID (:class:`UUIDMixin`);
* ``created_at`` / ``updated_at`` (:class:`TimestampMixin`);
* ``deleted_at`` — Soft Delete (:class:`SoftDeleteMixin`).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Единая схема именования ограничений — детерминированные имена для Alembic.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDMixin:
    """Первичный ключ типа UUID, генерируемый на стороне приложения."""

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4, sort_order=-100)


class TimestampMixin:
    """Временные метки создания и последнего обновления записи."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        sort_order=100,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        sort_order=101,
    )


class SoftDeleteMixin:
    """Мягкое удаление: запись помечается ``deleted_at`` вместо физического удаления."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True, index=True, sort_order=102
    )

    @property
    def is_deleted(self) -> bool:
        """Помечена ли запись как удалённая."""
        return self.deleted_at is not None
