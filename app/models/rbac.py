"""Модели RBAC: должности (роли), права и их связь."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    pass


class PermissionEntity(Base, UUIDMixin, TimestampMixin):
    """Справочник прав (сидируется из :mod:`app.permissions.registry`)."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(128))
    group: Mapped[str] = mapped_column(String(64), index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Permission {self.code}>"


class Role(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Должность с набором прав."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255), default=None)
    priority: Mapped[int] = mapped_column(default=0, nullable=False)
    is_system: Mapped[bool] = mapped_column(default=False, nullable=False)

    permissions: Mapped[list[RolePermission]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def permission_codes(self) -> set[str]:
        """Множество кодов прав, назначенных должности."""
        return {rp.permission_code for rp in self.permissions}

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Role {self.name!r} perms={len(self.permissions)}>"


class RolePermission(Base, UUIDMixin, TimestampMixin):
    """Назначение конкретного права должности (many-to-many)."""

    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_code", name="uq_role_permission"),)

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), index=True
    )
    permission_code: Mapped[str] = mapped_column(
        ForeignKey("permissions.code", ondelete="CASCADE"), index=True
    )

    role: Mapped[Role] = relationship(back_populates="permissions")
