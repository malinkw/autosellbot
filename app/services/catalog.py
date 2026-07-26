"""Служба каталога: просмотр и администрирование категорий и товаров."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ValidationError
from app.models import Category, Product
from app.repositories.catalog import CategoryRepository, ProductRepository
from app.repositories.review import ReviewRepository


class CatalogService:
    """Бизнес-логика каталога."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._categories = CategoryRepository(session)
        self._products = ProductRepository(session)
        self._reviews = ReviewRepository(session)

    # --- Витрина -------------------------------------------------------------
    async def root_categories(self, *, admin: bool = False) -> list[Category]:
        """Корневые категории (для витрины — только включённые)."""
        return await self._categories.roots(only_enabled=not admin)

    async def subcategories(self, parent_id: uuid.UUID, *, admin: bool = False) -> list[Category]:
        """Подкатегории категории."""
        return await self._categories.children(parent_id, only_enabled=not admin)

    async def products(self, category_id: uuid.UUID, *, admin: bool = False) -> list[Product]:
        """Товары категории."""
        return await self._products.in_category(category_id, visible_only=not admin)

    async def search_products(self, query: str) -> list[Product]:
        """Поиск товаров."""
        if len(query.strip()) < 2:
            raise ValidationError("Слишком короткий запрос для поиска.")
        return await self._products.search(query)

    async def all_products(self) -> list[Product]:
        """Все товары (для админ-панели)."""
        return await self._products.list(order_by=[Product.name])

    async def get_product(self, product_id: uuid.UUID) -> Product:
        """Карточка товара по ID."""
        product = await self._products.get(product_id)
        if product is None:
            raise NotFoundError("Товар не найден.")
        return product

    async def product_stock(self, product_id: uuid.UUID) -> int:
        """Наличие товара (число доступных позиций)."""
        return await self._products.available_stock(product_id)

    async def refresh_product_rating(self, product_id: uuid.UUID) -> None:
        """Пересчитать средний рейтинг и число отзывов товара."""
        avg, count = await self._reviews.product_aggregate(product_id)
        product = await self._products.get(product_id)
        if product is not None:
            product.rating = Decimal(str(round(avg, 2)))
            product.reviews_count = count
            await self._session.flush()

    # --- Администрирование категорий ----------------------------------------
    async def create_category(
        self,
        name: str,
        *,
        parent_id: uuid.UUID | None = None,
        description: str | None = None,
    ) -> Category:
        """Создать категорию/подкатегорию."""
        if not name.strip():
            raise ValidationError("Название категории не может быть пустым.")
        order = await self._categories.max_sort_order(parent_id) + 1
        return await self._categories.create(
            name=name.strip(),
            parent_id=parent_id,
            description=description,
            sort_order=order,
        )

    async def get_category(self, category_id: uuid.UUID) -> Category:
        """Категория по ID."""
        category = await self._categories.get(category_id)
        if category is None:
            raise NotFoundError("Категория не найдена.")
        return category

    async def update_category(self, category_id: uuid.UUID, **values: object) -> Category:
        """Обновить поля категории."""
        category = await self.get_category(category_id)
        return await self._categories.update(category, **values)

    async def set_category_enabled(self, category_id: uuid.UUID, enabled: bool) -> Category:
        """Включить/отключить категорию."""
        return await self.update_category(category_id, is_enabled=enabled)

    async def delete_category(self, category_id: uuid.UUID) -> None:
        """Мягко удалить категорию."""
        category = await self.get_category(category_id)
        await self._categories.soft_delete(category)

    # --- Администрирование товаров ------------------------------------------
    async def create_product(
        self,
        name: str,
        price: Decimal,
        *,
        category_id: uuid.UUID | None = None,
        description: str | None = None,
        photo_file_id: str | None = None,
    ) -> Product:
        """Создать товар."""
        if not name.strip():
            raise ValidationError("Название товара не может быть пустым.")
        if Decimal(price) <= 0:
            raise ValidationError("Цена должна быть больше нуля.")
        return await self._products.create(
            name=name.strip(),
            price=Decimal(price),
            category_id=category_id,
            description=description,
            photo_file_id=photo_file_id,
        )

    async def update_product(self, product_id: uuid.UUID, **values: object) -> Product:
        """Обновить поля товара."""
        product = await self.get_product(product_id)
        return await self._products.update(product, **values)

    async def delete_product(self, product_id: uuid.UUID) -> None:
        """Мягко удалить товар."""
        product = await self.get_product(product_id)
        await self._products.soft_delete(product)
