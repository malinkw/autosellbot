"""Утилиты форматирования для вывода в интерфейсе бота."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from app.config import get_settings


def money(amount: Decimal | int | float, *, symbol: str | None = None) -> str:
    """Отформатировать денежную сумму с символом валюты."""
    sym = symbol if symbol is not None else get_settings().app.currency_symbol
    value = Decimal(str(amount)).quantize(Decimal("0.01"))
    return f"{value:,.2f} {sym}".replace(",", " ")


def dt(value: datetime | None, *, fmt: str = "%d.%m.%Y %H:%M") -> str:
    """Отформатировать дату/время (или ``—`` для ``None``)."""
    return value.strftime(fmt) if value else "—"


def stars(rating: Decimal | int | float) -> str:
    """Строковое представление рейтинга звёздами."""
    full = max(0, min(5, round(float(rating))))
    return "★" * full + "☆" * (5 - full)
