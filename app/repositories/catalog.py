"""Репозитории каталога: категории и товары."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.sql.elements import ColumnElement

from app.models import Category, Position, Product
from app.models.enums import PositionStatus
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Доступ к категориям и подкатегориям."""

    model = Category

    async def roots(self, *, only_enabled: bool = True) -> list[Category]:
        """Корневые категории (без родителя)."""
        filters = [Category.parent_id.is_(None)]
        if only_enabled:
            filters.append(Category.is_enabled.is_(True))
        return await self.list(filters=filters, order_by=[Category.sort_order, Category.name])

    async def children(self, parent_id: uuid.UUID, *, only_enabled: bool = True) -> list[Category]:
        """Подкатегории указанной категории."""
        filters = [Category.parent_id == parent_id]
        if only_enabled:
            filters.append(Category.is_enabled.is_(True))
        return await self.list(filters=filters, order_by=[Category.sort_order, Category.name])

    async def max_sort_order(self, parent_id: uuid.UUID | None) -> int:
        """Максимальный порядковый номер среди соседних категорий."""
        stmt = select(func.coalesce(func.max(Category.sort_order), 0)).where(
            Category.parent_id == parent_id, Category.deleted_at.is_(None)
        )
        return int((await self.session.execute(stmt)).scalar_one())


class ProductRepository(BaseRepository[Product]):
    """Доступ к товарам."""

    model = Product

    async def in_category(
        self, category_id: uuid.UUID, *, visible_only: bool = True
    ) -> list[Product]:
        """Товары категории."""
        filters = [Product.category_id == category_id]
        if visible_only:
            filters += [Product.is_hidden.is_(False), Product.is_archived.is_(False)]
        return await self.list(filters=filters, order_by=[Product.sort_order, Product.name])

    async def search(self, query: str, *, visible_only: bool = True) -> list[Product]:
        """Поиск товаров по названию/описанию."""
        like = f"%{query.strip()}%"
        filters: list[ColumnElement[bool]] = [
            Product.name.ilike(like) | Product.description.ilike(like)
        ]
        if visible_only:
            filters += [Product.is_hidden.is_(False), Product.is_archived.is_(False)]
        return await self.list(filters=filters, order_by=[Product.name], limit=30)

    async def available_stock(self, product_id: uuid.UUID) -> int:
        """Количество доступных позиций товара (наличие)."""
        stmt = select(func.count()).where(
            Position.product_id == product_id,
            Position.status == PositionStatus.AVAILABLE,
            Position.deleted_at.is_(None),
        )
        return int((await self.session.execute(stmt)).scalar_one())
