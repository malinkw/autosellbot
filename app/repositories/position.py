"""Репозиторий позиций выдачи."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models import Position
from app.models.enums import PositionStatus
from app.repositories.base import BaseRepository


class PositionRepository(BaseRepository[Position]):
    """Доступ к позициям выдачи."""

    model = Position

    async def available_for_product(self, product_id: uuid.UUID) -> list[Position]:
        """Доступные позиции товара."""
        return await self.list(
            filters=[
                Position.product_id == product_id,
                Position.status == PositionStatus.AVAILABLE,
            ],
            order_by=[Position.created_at],
        )

    async def lock_available(self, product_id: uuid.UUID) -> Position | None:
        """Заблокировать (FOR UPDATE SKIP LOCKED) одну доступную позицию товара.

        Защита от Race Condition при одновременной покупке: конкурентные
        транзакции не смогут выбрать одну и ту же позицию.
        """
        stmt = (
            select(Position)
            .where(
                Position.product_id == product_id,
                Position.status == PositionStatus.AVAILABLE,
                Position.deleted_at.is_(None),
            )
            .order_by(Position.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        return (await self.session.execute(stmt)).scalars().first()
