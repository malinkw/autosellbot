"""Модели каталога: категории (с подкатегориями) и товары."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.position import Position


class Category(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Категория каталога.

    Подкатегория — это категория с заполненным ``parent_id`` (самоссылка).
    """

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), default=None, index=True
    )
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False, index=True)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)

    parent: Mapped[Category | None] = relationship(remote_side="Category.id", backref="children")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Category {self.name!r}>"


class Product(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Товар каталога."""

    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), default=None, index=True
    )
    photo_file_id: Mapped[str | None] = mapped_column(String(255), default=None)
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.00"), nullable=False)
    reviews_count: Mapped[int] = mapped_column(default=0, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False, index=True)
    is_hidden: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(default=False, nullable=False)

    category: Mapped[Category | None] = relationship(lazy="selectin")
    positions: Mapped[list[Position]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Product {self.name!r} price={self.price}>"
