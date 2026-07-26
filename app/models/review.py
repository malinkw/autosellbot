"""Модель отзыва о товаре по завершённому заказу."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.catalog import Product
    from app.models.user import User


class Review(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Отзыв с оценкой 0–5. Модерируется администрацией."""

    __tablename__ = "reviews"
    __table_args__ = (CheckConstraint("rating >= 0 AND rating <= 5", name="rating_range"),)

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    text: Mapped[str | None] = mapped_column(Text, default=None)
    is_hidden: Mapped[bool] = mapped_column(default=False, nullable=False)
    admin_reply: Mapped[str | None] = mapped_column(Text, default=None)
    replied_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )

    product: Mapped[Product] = relationship(lazy="selectin")
    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="selectin")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Review order={self.order_id} rating={self.rating}>"
