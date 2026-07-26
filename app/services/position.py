"""Служба позиций выдачи."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ValidationError
from app.models import Position, User
from app.models.enums import PositionStatus
from app.repositories.position import PositionRepository


class PositionService:
    """CRUD и управление статусами позиций."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PositionRepository(session)

    async def create(
        self,
        *,
        product_id: uuid.UUID,
        content: str,
        creator: User,
        district_id: uuid.UUID | None = None,
        location_id: uuid.UUID | None = None,
        price_override: Decimal | None = None,
    ) -> Position:
        """Создать позицию. ``creator`` фиксируется как автор (важно для диспутов)."""
        if not content.strip():
            raise ValidationError("Содержимое позиции не может быть пустым.")
        return await self._repo.create(
            product_id=product_id,
            content=content.strip(),
            created_by_id=creator.id,
            district_id=district_id,
            location_id=location_id,
            price_override=price_override,
        )

    async def get(self, position_id: uuid.UUID) -> Position:
        position = await self._repo.get(position_id)
        if position is None:
            raise NotFoundError("Позиция не найдена.")
        return position

    async def list_for_product(self, product_id: uuid.UUID) -> list[Position]:
        """Все позиции товара."""
        return await self._repo.list(
            filters=[Position.product_id == product_id],
            order_by=[Position.created_at.desc()],
        )

    async def update(self, position_id: uuid.UUID, **values: object) -> Position:
        """Обновить поля позиции."""
        position = await self.get(position_id)
        return await self._repo.update(position, **values)

    async def change_status(self, position_id: uuid.UUID, status: PositionStatus) -> Position:
        """Изменить статус позиции."""
        return await self.update(position_id, status=status)

    async def archive(self, position_id: uuid.UUID) -> Position:
        """Архивировать позицию."""
        return await self.change_status(position_id, PositionStatus.ARCHIVED)

    async def delete(self, position_id: uuid.UUID) -> None:
        """Мягко удалить позицию."""
        position = await self.get(position_id)
        await self._repo.soft_delete(position)
