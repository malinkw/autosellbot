"""Служба должностей и назначения прав (RBAC-администрирование)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationError
from app.models import Role, RolePermission
from app.permissions import Permission
from app.repositories.rbac import RolePermissionRepository, RoleRepository


class RoleService:
    """CRUD должностей и управление их правами."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._roles = RoleRepository(session)
        self._role_perms = RolePermissionRepository(session)

    async def list_all(self) -> list[Role]:
        """Все должности."""
        return await self._roles.list_all()

    async def get(self, role_id: uuid.UUID) -> Role:
        role = await self._roles.get(role_id)
        if role is None:
            raise NotFoundError("Должность не найдена.")
        return role

    async def create(self, name: str, *, description: str | None = None, priority: int = 0) -> Role:
        """Создать должность."""
        if not name.strip():
            raise ValidationError("Название должности не может быть пустым.")
        if await self._roles.get_by_name(name.strip()) is not None:
            raise ConflictError("Должность с таким именем уже существует.")
        return await self._roles.create(
            name=name.strip(), description=description, priority=priority
        )

    async def update(self, role_id: uuid.UUID, **values: object) -> Role:
        """Обновить должность."""
        role = await self.get(role_id)
        return await self._roles.update(role, **values)

    async def delete(self, role_id: uuid.UUID) -> None:
        """Удалить должность (системную удалять нельзя)."""
        role = await self.get(role_id)
        if role.is_system:
            raise BusinessRuleError("Системную должность удалить нельзя.")
        if await self._roles.count_members(role.id) > 0:
            raise BusinessRuleError("Нельзя удалить должность с назначенными сотрудниками.")
        await self._roles.soft_delete(role)

    # --- Управление правами --------------------------------------------------
    @staticmethod
    def _validate_codes(codes: Iterable[str]) -> set[str]:
        valid = {p.value for p in Permission}
        selected = set(codes)
        unknown = selected - valid
        if unknown:
            raise ValidationError(f"Неизвестные права: {sorted(unknown)}")
        return selected

    async def set_permissions(self, role_id: uuid.UUID, codes: Iterable[str]) -> Role:
        """Полностью заменить набор прав должности."""
        role = await self.get(role_id)
        target = self._validate_codes(codes)
        current = {rp.permission_code: rp for rp in role.permissions}

        for code in target - set(current):
            self._session.add(RolePermission(role_id=role.id, permission_code=code))
        for code in set(current) - target:
            await self._session.delete(current[code])
        await self._session.flush()
        await self._session.refresh(role)
        return role

    async def toggle_permission(self, role_id: uuid.UUID, code: str) -> Role:
        """Включить/выключить одно право должности."""
        role = await self.get(role_id)
        self._validate_codes([code])
        current = role.permission_codes
        new_codes = current - {code} if code in current else current | {code}
        return await self.set_permissions(role_id, new_codes)

    async def copy_permissions(self, source_id: uuid.UUID, target_id: uuid.UUID) -> Role:
        """Скопировать права одной должности в другую."""
        source = await self.get(source_id)
        return await self.set_permissions(target_id, source.permission_codes)

    async def export_permissions(self, role_id: uuid.UUID) -> list[str]:
        """Экспортировать коды прав должности."""
        role = await self.get(role_id)
        return sorted(role.permission_codes)

    async def import_permissions(self, role_id: uuid.UUID, codes: Iterable[str]) -> Role:
        """Импортировать (заменить) права должности из списка кодов."""
        return await self.set_permissions(role_id, codes)
