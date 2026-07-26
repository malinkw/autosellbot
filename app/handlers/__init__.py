"""Регистрация всех роутеров бота."""

from __future__ import annotations

from aiogram import Router


def get_routers() -> list[Router]:
    """Вернуть все роутеры в порядке подключения (ошибки — первыми)."""
    from app.handlers import (
        catalog,
        disputes,
        errors,
        menu,
        orders,
        reviews,
        start,
        wallet,
    )
    from app.handlers.admin import get_admin_routers

    return [
        errors.router,
        start.router,
        menu.router,
        catalog.router,
        orders.router,
        wallet.router,
        disputes.router,
        reviews.router,
        *get_admin_routers(),
    ]
