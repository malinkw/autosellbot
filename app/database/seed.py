"""Идемпотентный сидинг справочных данных.

Выполняется при старте приложения после применения миграций:

* синхронизирует таблицу ``permissions`` с реестром :mod:`app.permissions.registry`;
* создаёт системную должность «Владелец» со всеми правами;
* создаёт набор настроек бота по умолчанию.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models import BotSetting, PermissionEntity, Role, RolePermission
from app.permissions import PERMISSION_METADATA, Permission

log = get_logger("bot")

OWNER_ROLE_NAME = "Владелец"

DEFAULT_SETTINGS: dict[str, tuple[str, Any]] = {
    "maintenance_mode": ("Режим обслуживания", False),
    "welcome_message": ("Приветственное сообщение", "Добро пожаловать в магазин!"),
    "support_contacts": ("Контакты поддержки", "@support"),
    "rules": ("Правила", "Правила магазина не заданы."),
    "faq": ("FAQ", "Часто задаваемые вопросы не заданы."),
    "min_topup": ("Минимальная сумма пополнения", 100),
    "max_topup": ("Максимальная сумма пополнения", 100000),
    "notifications_enabled": ("Уведомления включены", True),
    "currency": ("Валюта", "RUB"),
}


async def seed_permissions(session: AsyncSession) -> int:
    """Синхронизировать таблицу прав с реестром. Возвращает число добавленных."""
    existing = set((await session.execute(select(PermissionEntity.code))).scalars().all())
    added = 0
    for permission in Permission:
        meta = PERMISSION_METADATA[permission]
        if permission.value not in existing:
            session.add(
                PermissionEntity(code=permission.value, title=meta.title, group=str(meta.group))
            )
            added += 1
    await session.flush()
    return added


async def seed_owner_role(session: AsyncSession) -> Role:
    """Создать/дополнить системную должность «Владелец» со всеми правами."""
    role = (
        await session.execute(select(Role).where(Role.name == OWNER_ROLE_NAME))
    ).scalar_one_or_none()
    if role is None:
        role = Role(
            name=OWNER_ROLE_NAME,
            description="Полный доступ ко всем функциям системы",
            priority=1000,
            is_system=True,
        )
        session.add(role)
        await session.flush()

    # Явный async-запрос вместо ленивого обращения к role.permissions.
    current = set(
        (
            await session.execute(
                select(RolePermission.permission_code).where(RolePermission.role_id == role.id)
            )
        )
        .scalars()
        .all()
    )
    for permission in Permission:
        if permission.value not in current:
            session.add(RolePermission(role_id=role.id, permission_code=permission.value))
    await session.flush()
    return role


async def seed_settings(session: AsyncSession) -> int:
    """Создать отсутствующие настройки по умолчанию. Возвращает число добавленных."""
    existing = set((await session.execute(select(BotSetting.key))).scalars().all())
    added = 0
    for key, (title, value) in DEFAULT_SETTINGS.items():
        if key not in existing:
            session.add(BotSetting(key=key, title=title, value=value))
            added += 1
    await session.flush()
    return added


async def seed_all(session: AsyncSession) -> None:
    """Выполнить весь сидинг в одной транзакции."""
    perms = await seed_permissions(session)
    await seed_owner_role(session)
    settings = await seed_settings(session)
    await session.commit()
    log.info("seed_completed", permissions_added=perms, settings_added=settings)
