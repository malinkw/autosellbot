"""Модель пользователя (и сотрудника — это пользователь с назначенной должностью)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import AccountStatus

if TYPE_CHECKING:
    from app.models.rbac import Role


class User(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Пользователь бота.

    Сотрудник — это тот же пользователь, у которого выставлен ``is_staff`` и
    назначена должность ``role``. Владельцы (из ``BOT__ADMIN_IDS``) обладают
    безусловными суперправами независимо от роли.
    """

    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    public_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), default=None)
    nickname: Mapped[str | None] = mapped_column(String(32), unique=True, default=None, index=True)
    balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00"), nullable=False
    )
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, native_enum=False, length=16),
        default=AccountStatus.ACTIVE,
        nullable=False,
    )
    is_staff: Mapped[bool] = mapped_column(default=False, nullable=False)
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("roles.id", ondelete="SET NULL"), default=None, index=True
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    onboarded: Mapped[bool] = mapped_column(default=False, nullable=False)

    role: Mapped[Role | None] = relationship(lazy="selectin")

    def __repr__(self) -> str:  # pragma: no cover - отладочное представление
        return f"<User {self.public_id} tg={self.telegram_id} nick={self.nickname!r}>"
