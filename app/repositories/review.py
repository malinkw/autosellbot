"""Репозиторий отзывов."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models import Review
from app.repositories.base import BaseRepository


class ReviewRepository(BaseRepository[Review]):
    """Доступ к отзывам."""

    model = Review

    async def get_by_order(self, order_id: uuid.UUID) -> Review | None:
        """Отзыв по заказу (не более одного на заказ)."""
        return await self.get_by(order_id=order_id)

    async def for_product(
        self, product_id: uuid.UUID, *, visible_only: bool = True
    ) -> list[Review]:
        """Отзывы о товаре."""
        filters = [Review.product_id == product_id]
        if visible_only:
            filters.append(Review.is_hidden.is_(False))
        return await self.list(filters=filters, order_by=[Review.created_at.desc()])

    async def product_aggregate(self, product_id: uuid.UUID) -> tuple[float, int]:
        """Средний рейтинг и число видимых отзывов о товаре."""
        stmt = select(
            func.coalesce(func.avg(Review.rating), 0.0),
            func.count(Review.id),
        ).where(
            Review.product_id == product_id,
            Review.is_hidden.is_(False),
            Review.deleted_at.is_(None),
        )
        avg, count = (await self.session.execute(stmt)).one()
        return float(avg), int(count)
