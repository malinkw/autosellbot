"""Базовый обобщённый репозиторий с поддержкой Soft Delete и пагинации."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.database.base import Base, SoftDeleteMixin
from app.utils.pagination import Page, Paginator


class BaseRepository[ModelT: Base]:
    """Обобщённый CRUD-репозиторий.

    Все выборки по умолчанию исключают мягко удалённые записи (если модель
    поддерживает Soft Delete). Наследники указывают ``model``.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- Внутренние помощники ------------------------------------------------
    @property
    def _supports_soft_delete(self) -> bool:
        return issubclass(self.model, SoftDeleteMixin)

    def _base_select(self, *, include_deleted: bool = False) -> Select[tuple[ModelT]]:
        stmt = select(self.model)
        if self._supports_soft_delete and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return stmt

    # --- Чтение --------------------------------------------------------------
    async def get(self, entity_id: uuid.UUID, *, include_deleted: bool = False) -> ModelT | None:
        """Получить запись по первичному ключу."""
        stmt = self._base_select(include_deleted=include_deleted).where(
            self.model.id == entity_id  # type: ignore[attr-defined]
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by(self, **filters: Any) -> ModelT | None:
        """Получить первую запись, удовлетворяющую равенствам полей."""
        stmt = self._apply_filters(self._base_select(), filters)
        return (await self.session.execute(stmt)).scalars().first()

    async def list(
        self,
        *,
        filters: Sequence[ColumnElement[bool]] | None = None,
        order_by: Sequence[Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        include_deleted: bool = False,
    ) -> list[ModelT]:
        """Вернуть список записей по условиям."""
        stmt = self._base_select(include_deleted=include_deleted)
        if filters:
            stmt = stmt.where(*filters)
        if order_by:
            stmt = stmt.order_by(*order_by)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count(
        self,
        *,
        filters: Sequence[ColumnElement[bool]] | None = None,
        include_deleted: bool = False,
    ) -> int:
        """Подсчитать количество записей по условиям."""
        stmt = select(func.count()).select_from(self.model)
        if self._supports_soft_delete and not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        if filters:
            stmt = stmt.where(*filters)
        return int((await self.session.execute(stmt)).scalar_one())

    async def paginate(
        self,
        paginator: Paginator,
        *,
        filters: Sequence[ColumnElement[bool]] | None = None,
        order_by: Sequence[Any] | None = None,
        include_deleted: bool = False,
    ) -> Page[ModelT]:
        """Постранично выбрать записи вместе с общим количеством."""
        total = await self.count(filters=filters, include_deleted=include_deleted)
        items = await self.list(
            filters=filters,
            order_by=order_by,
            limit=paginator.limit,
            offset=paginator.offset,
            include_deleted=include_deleted,
        )
        return paginator.build(items, total)

    async def exists(self, **filters: Any) -> bool:
        """Проверить существование записи по равенствам полей."""
        return (await self.get_by(**filters)) is not None

    # --- Запись --------------------------------------------------------------
    async def create(self, **values: Any) -> ModelT:
        """Создать и добавить запись (без коммита)."""
        instance = self.model(**values)
        self.session.add(instance)
        await self.session.flush()
        return instance

    def add(self, instance: ModelT) -> ModelT:
        """Добавить готовый экземпляр в сессию."""
        self.session.add(instance)
        return instance

    async def update(self, instance: ModelT, **values: Any) -> ModelT:
        """Обновить поля экземпляра."""
        for key, value in values.items():
            setattr(instance, key, value)
        await self.session.flush()
        return instance

    async def soft_delete(self, instance: ModelT) -> None:
        """Мягко удалить запись (проставить ``deleted_at``)."""
        if not self._supports_soft_delete:
            raise TypeError(f"{self.model.__name__} не поддерживает Soft Delete")
        from datetime import UTC, datetime

        instance.deleted_at = datetime.now(UTC)  # type: ignore[attr-defined]
        await self.session.flush()

    async def hard_delete(self, instance: ModelT) -> None:
        """Физически удалить запись."""
        await self.session.delete(instance)
        await self.session.flush()

    def _apply_filters(
        self, stmt: Select[tuple[ModelT]], filters: dict[str, Any]
    ) -> Select[tuple[ModelT]]:
        for field, value in filters.items():
            stmt = stmt.where(getattr(self.model, field) == value)
        return stmt
