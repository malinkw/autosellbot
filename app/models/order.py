"""Модели заказа и истории смены статусов."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import OrderStatus

if TYPE_CHECKING:
    from app.models.catalog import Product
    from app.models.position import Position
    from app.models.user import User


class Order(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Заказ. История заказов хранится бессрочно (Soft Delete не физический)."""

    __tablename__ = "orders"

    number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), default=None, index=True
    )
    position_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("positions.id", ondelete="SET NULL"), default=None, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=32),
        default=OrderStatus.CREATED,
        nullable=False,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    user: Mapped[User] = relationship(lazy="selectin")
    product: Mapped[Product | None] = relationship(lazy="selectin")
    position: Mapped[Position | None] = relationship(lazy="selectin")
    history: Mapped[list[OrderStatusHistory]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Order {self.number} status={self.status}>"


class OrderStatusHistory(Base, UUIDMixin, TimestampMixin):
    """Неизменяемая запись о смене статуса заказа."""

    __tablename__ = "order_status_history"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=False, length=32), nullable=False
    )
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    comment: Mapped[str | None] = mapped_column(Text, default=None)

    order: Mapped[Order] = relationship(back_populates="history")
