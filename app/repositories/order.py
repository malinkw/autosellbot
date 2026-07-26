"""Репозиторий заказов."""

from __future__ import annotations

import uuid

from app.models import Order
from app.models.enums import OrderStatus
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Доступ к заказам."""

    model = Order

    async def get_by_number(self, number: str) -> Order | None:
        """Найти заказ по номеру."""
        return await self.get_by(number=number)

    async def for_user(self, user_id: uuid.UUID) -> list[Order]:
        """История заказов пользователя (хранится бессрочно)."""
        return await self.list(
            filters=[Order.user_id == user_id], order_by=[Order.created_at.desc()]
        )

    async def by_status(self, status: OrderStatus) -> list[Order]:
        """Заказы в указанном статусе."""
        return await self.list(filters=[Order.status == status], order_by=[Order.created_at.desc()])
