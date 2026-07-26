"""Утилиты пагинации."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil


@dataclass(slots=True)
class Page[T]:
    """Одна страница результатов выборки."""

    items: list[T] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 8

    @property
    def pages(self) -> int:
        """Общее число страниц (минимум 1)."""
        return max(1, ceil(self.total / self.page_size)) if self.page_size else 1

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(slots=True)
class Paginator:
    """Помощник расчёта смещений для запросов."""

    page: int = 1
    page_size: int = 8

    def __post_init__(self) -> None:
        self.page = max(1, self.page)
        self.page_size = max(1, self.page_size)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size

    def build[T](self, items: list[T], total: int) -> Page[T]:
        """Собрать :class:`Page` из выборки и общего количества."""
        return Page(items=items, total=total, page=self.page, page_size=self.page_size)
