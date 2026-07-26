"""Репозитории RBAC (должности и права)."""

from __future__ import annotations

from sqlalchemy import select

from app.models import PermissionEntity, Role, RolePermission
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    """Доступ к должностям."""

    model = Role

    async def get_by_name(self, name: str) -> Role | None:
        """Найти должность по имени."""
        return await self.get_by(name=name)

    async def list_all(self) -> list[Role]:
        """Все должности, отсортированные по приоритету."""
        return await self.list(order_by=[Role.priority.desc(), Role.name])

    async def count_members(self, role_id: object) -> int:
        """Количество сотрудников с данной должностью."""
        from app.models import User

        stmt = select(User).where(User.role_id == role_id, User.deleted_at.is_(None))
        return len((await self.session.execute(stmt)).scalars().all())


class RolePermissionRepository(BaseRepository[RolePermission]):
    """Доступ к назначениям прав должностям."""

    model = RolePermission

    async def codes_for_role(self, role_id: object) -> set[str]:
        """Множество кодов прав, назначенных должности."""
        stmt = select(RolePermission.permission_code).where(RolePermission.role_id == role_id)
        return set((await self.session.execute(stmt)).scalars().all())


class PermissionRepository(BaseRepository[PermissionEntity]):
    """Доступ к справочнику прав."""

    model = PermissionEntity

    async def all_codes(self) -> set[str]:
        """Все зарегистрированные коды прав."""
        stmt = select(PermissionEntity.code)
        return set((await self.session.execute(stmt)).scalars().all())
