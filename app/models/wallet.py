"""Модели кошелька: операции, заявки на пополнение и платёжные реквизиты."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import RequisiteType, TopUpStatus, TransactionType

if TYPE_CHECKING:
    from app.models.user import User


class Transaction(Base, UUIDMixin, TimestampMixin):
    """Неизменяемая запись об операции по балансу пользователя.

    ``amount`` — знаковая величина (пополнение/начисление/возврат > 0, списание < 0).
    ``balance_after`` фиксирует баланс после операции для аудита.
    """

    __tablename__ = "transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, native_enum=False, length=16), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
    comment: Mapped[str | None] = mapped_column(Text, default=None)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="selectin")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Transaction {self.type} {self.amount}>"


class TopUpRequest(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Заявка на пополнение баланса с прикреплённым PDF-чеком."""

    __tablename__ = "topup_requests"

    number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    receipt_file_id: Mapped[str | None] = mapped_column(String(255), default=None)
    receipt_file_name: Mapped[str | None] = mapped_column(String(255), default=None)
    status: Mapped[TopUpStatus] = mapped_column(
        Enum(TopUpStatus, native_enum=False, length=16),
        default=TopUpStatus.CREATED,
        nullable=False,
        index=True,
    )
    comment: Mapped[str | None] = mapped_column(Text, default=None)
    processed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="selectin")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TopUpRequest {self.number} status={self.status}>"


class Requisite(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Платёжный реквизит (карта или СБП)."""

    __tablename__ = "requisites"

    type: Mapped[RequisiteType] = mapped_column(
        Enum(RequisiteType, native_enum=False, length=8), nullable=False
    )
    value: Mapped[str] = mapped_column(String(64))
    holder: Mapped[str | None] = mapped_column(String(128), default=None)
    bank: Mapped[str | None] = mapped_column(String(128), default=None)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    priority: Mapped[int] = mapped_column(default=0, nullable=False, index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Requisite {self.type} {self.value}>"
