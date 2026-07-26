"""Начальная схема БД (baseline).

Создаёт полную схему из моделей приложения. Схема формируется из
``Base.metadata`` — единого источника правды, что гарантирует полное
соответствие таблиц ORM-моделям. Последующие изменения оформляются
обычными автогенерируемыми ревизиями Alembic.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-26 00:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
from app.models import Base

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Создать все таблицы схемы."""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Удалить все таблицы схемы."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
