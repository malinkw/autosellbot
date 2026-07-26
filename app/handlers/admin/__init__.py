"""Роутеры административной панели."""

from __future__ import annotations

from aiogram import Router


def get_admin_routers() -> list[Router]:
    """Вернуть все админские роутеры в порядке подключения."""
    from app.handlers.admin import (
        accounting,
        backup,
        catalog,
        disputes,
        locality,
        logs,
        positions,
        requisites,
        reviews,
        roles,
        settings,
        staff,
        stats,
        topups,
        users,
    )

    return [
        users.router,
        catalog.router,
        positions.router,
        locality.router,
        staff.router,
        roles.router,
        topups.router,
        disputes.router,
        reviews.router,
        accounting.router,
        requisites.router,
        settings.router,
        logs.router,
        stats.router,
        backup.router,
    ]
