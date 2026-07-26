"""Служба платёжных реквизитов."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ValidationError
from app.models import Requisite
from app.models.enums import RequisiteType
from app.repositories.wallet import RequisiteRepository


class RequisiteService:
    """CRUD и управление платёжными реквизитами."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = RequisiteRepository(session)

    async def active(self) -> list[Requisite]:
        """Активные реквизиты (для показа при пополнении)."""
        return await self._repo.active()

    async def all(self) -> list[Requisite]:
        """Все реквизиты по приоритету."""
        return await self._repo.all_ordered()

    async def create(
        self,
        *,
        type_: RequisiteType,
        value: str,
        holder: str | None = None,
        bank: str | None = None,
        priority: int = 0,
    ) -> Requisite:
        """Создать реквизит."""
        if not value.strip():
            raise ValidationError("Значение реквизита не может быть пустым.")
        return await self._repo.create(
            type=type_,
            value=value.strip(),
            holder=holder,
            bank=bank,
            priority=priority,
        )

    async def get(self, requisite_id: uuid.UUID) -> Requisite:
        requisite = await self._repo.get(requisite_id)
        if requisite is None:
            raise NotFoundError("Реквизит не найден.")
        return requisite

    async def update(self, requisite_id: uuid.UUID, **values: object) -> Requisite:
        """Обновить реквизит."""
        requisite = await self.get(requisite_id)
        return await self._repo.update(requisite, **values)

    async def set_active(self, requisite_id: uuid.UUID, active: bool) -> Requisite:
        """Включить/отключить реквизит."""
        return await self.update(requisite_id, is_active=active)

    async def set_priority(self, requisite_id: uuid.UUID, priority: int) -> Requisite:
        """Изменить приоритет отображения."""
        return await self.update(requisite_id, priority=priority)

    async def delete(self, requisite_id: uuid.UUID) -> None:
        """Мягко удалить реквизит."""
        requisite = await self.get(requisite_id)
        await self._repo.soft_delete(requisite)
