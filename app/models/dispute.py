"""Модели диспута: сам диспут, участники, сообщения и неизменяемая история."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import DisputeActionType, DisputeStatus

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class Dispute(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Диспут по завершённому заказу."""

    __tablename__ = "disputes"

    number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True, index=True
    )
    opener_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    responsible_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None, index=True
    )
    subject: Mapped[str] = mapped_column(Text)
    status: Mapped[DisputeStatus] = mapped_column(
        Enum(DisputeStatus, native_enum=False, length=16),
        default=DisputeStatus.OPEN,
        nullable=False,
        index=True,
    )
    resolution: Mapped[str | None] = mapped_column(Text, default=None)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    order: Mapped[Order] = relationship(lazy="selectin")
    participants: Mapped[list[DisputeParticipant]] = relationship(
        back_populates="dispute", cascade="all, delete-orphan", lazy="selectin"
    )
    messages: Mapped[list[DisputeMessage]] = relationship(
        back_populates="dispute",
        cascade="all, delete-orphan",
        order_by="DisputeMessage.created_at",
    )
    history: Mapped[list[DisputeHistory]] = relationship(
        back_populates="dispute",
        cascade="all, delete-orphan",
        order_by="DisputeHistory.created_at",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Dispute {self.number} status={self.status}>"


class DisputeParticipant(Base, UUIDMixin, TimestampMixin):
    """Сотрудник-участник диспута (добавляется автоматически или вручную)."""

    __tablename__ = "dispute_participants"

    dispute_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("disputes.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    reason: Mapped[str] = mapped_column(String(255))
    auto_added: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    dispute: Mapped[Dispute] = relationship(back_populates="participants")
    user: Mapped[User] = relationship(lazy="selectin")


class DisputeMessage(Base, UUIDMixin, TimestampMixin):
    """Сообщение в переписке диспута (может содержать вложение)."""

    __tablename__ = "dispute_messages"

    dispute_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("disputes.id", ondelete="CASCADE"), index=True
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    text: Mapped[str | None] = mapped_column(Text, default=None)
    file_id: Mapped[str | None] = mapped_column(String(255), default=None)

    dispute: Mapped[Dispute] = relationship(back_populates="messages")
    sender: Mapped[User] = relationship(lazy="selectin")


class DisputeHistory(Base, UUIDMixin, TimestampMixin):
    """Неизменяемая история действий диспута (удаление запрещено на уровне логики)."""

    __tablename__ = "dispute_history"

    dispute_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("disputes.id", ondelete="CASCADE"), index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    action: Mapped[DisputeActionType] = mapped_column(
        Enum(DisputeActionType, native_enum=False, length=32), nullable=False
    )
    details: Mapped[str | None] = mapped_column(Text, default=None)

    dispute: Mapped[Dispute] = relationship(back_populates="history")
    actor: Mapped[User | None] = relationship(lazy="selectin")
