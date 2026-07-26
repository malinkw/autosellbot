"""Служба отзывов: создание и модерация."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationError
from app.models import Review, User
from app.models.enums import OrderStatus
from app.repositories.order import OrderRepository
from app.repositories.review import ReviewRepository
from app.services.catalog import CatalogService


class ReviewService:
    """Бизнес-логика отзывов."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ReviewRepository(session)
        self._orders = OrderRepository(session)
        self._catalog = CatalogService(session)

    async def create(
        self, user: User, order_id: uuid.UUID, *, rating: int, text: str | None = None
    ) -> Review:
        """Оставить отзыв по завершённому заказу (оценка 0–5)."""
        if not 0 <= rating <= 5:
            raise ValidationError("Оценка должна быть от 0 до 5.")
        order = await self._orders.get(order_id)
        if order is None or order.user_id != user.id:
            raise NotFoundError("Заказ не найден.")
        if order.status != OrderStatus.COMPLETED:
            raise BusinessRuleError("Отзыв можно оставить только по завершённому заказу.")
        if order.product_id is None:
            raise BusinessRuleError("По заказу нельзя оставить отзыв: товар недоступен.")
        if await self._repo.get_by_order(order.id) is not None:
            raise ConflictError("Вы уже оставили отзыв по этому заказу.")

        review = await self._repo.create(
            order_id=order.id,
            product_id=order.product_id,
            user_id=user.id,
            rating=rating,
            text=(text or None),
        )
        await self._catalog.refresh_product_rating(order.product_id)
        return review

    async def get(self, review_id: uuid.UUID) -> Review:
        review = await self._repo.get(review_id)
        if review is None:
            raise NotFoundError("Отзыв не найден.")
        return review

    async def get_for_order(self, order_id: uuid.UUID) -> Review | None:
        """Отзыв по заказу (если оставлен)."""
        return await self._repo.get_by_order(order_id)

    async def for_product(self, product_id: uuid.UUID, *, admin: bool = False) -> list[Review]:
        """Отзывы о товаре."""
        return await self._repo.for_product(product_id, visible_only=not admin)

    async def recent(self, *, limit: int = 20) -> list[Review]:
        """Последние отзывы (для модерации в админ-панели)."""
        return await self._repo.list(order_by=[Review.created_at.desc()], limit=limit)

    async def reply(self, review_id: uuid.UUID, admin: User, text: str) -> Review:
        """Ответить на отзыв (администрация)."""
        review = await self.get(review_id)
        review.admin_reply = text
        review.replied_by_id = admin.id
        await self._session.flush()
        return review

    async def set_hidden(self, review_id: uuid.UUID, hidden: bool) -> Review:
        """Скрыть/показать отзыв и пересчитать рейтинг товара."""
        review = await self.get(review_id)
        review.is_hidden = hidden
        await self._session.flush()
        await self._catalog.refresh_product_rating(review.product_id)
        return review

    async def delete(self, review_id: uuid.UUID) -> None:
        """Мягко удалить отзыв и пересчитать рейтинг товара."""
        review = await self.get(review_id)
        product_id = review.product_id
        await self._repo.soft_delete(review)
        await self._catalog.refresh_product_rating(product_id)
