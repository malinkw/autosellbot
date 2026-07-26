"""Модель позиции выдачи (конкретная единица товара в районе/локации)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.enums import PositionStatus

if TYPE_CHECKING:
    from app.models.catalog import Product
    from app.models.locality import District, Location
    from app.models.user import User


class Position(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Позиция выдачи.

    ``created_by_id`` — сотрудник, создавший позицию. По ТЗ именно он по умолчанию
    становится ответственным по диспуту и всегда добавляется в его участники.
    """

    __tablename__ = "positions"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    district_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("districts.id", ondelete="SET NULL"), default=None, index=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), default=None, index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None, index=True
    )
    content: Mapped[str] = mapped_column(Text)
    price_override: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), default=None)
    status: Mapped[PositionStatus] = mapped_column(
        Enum(PositionStatus, native_enum=False, length=16),
        default=PositionStatus.AVAILABLE,
        nullable=False,
        index=True,
    )

    product: Mapped[Product] = relationship(back_populates="positions", lazy="selectin")
    district: Mapped[District | None] = relationship(lazy="selectin")
    location: Mapped[Location | None] = relationship(lazy="selectin")
    created_by: Mapped[User | None] = relationship(lazy="selectin")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Position {self.id} status={self.status}>"
