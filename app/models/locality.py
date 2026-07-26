"""Модели местности: районы и кастомные локации."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class District(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Район выдачи."""

    __tablename__ = "districts"

    name: Mapped[str] = mapped_column(String(128), index=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<District {self.name!r}>"


class Location(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Кастомная локация выдачи."""

    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Location {self.name!r}>"
