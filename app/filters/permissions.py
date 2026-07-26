"""Фильтры проверки прав доступа (RBAC) на уровне роутеров и хендлеров."""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import TelegramObject

from app.models import User
from app.permissions import Permission
from app.services import ServiceContainer


class IsAdmin(BaseFilter):
    """Пропускает только пользователей с доступом в админ-панель."""

    async def __call__(self, event: TelegramObject, user: User, services: ServiceContainer) -> bool:
        return services.permissions.is_admin(user)


class IsOwner(BaseFilter):
    """Пропускает только владельцев (Telegram ID из настроек)."""

    async def __call__(self, event: TelegramObject, user: User, services: ServiceContainer) -> bool:
        return services.permissions.is_owner(user)


class HasPermission(BaseFilter):
    """Пропускает пользователей с указанным правом."""

    def __init__(self, permission: Permission) -> None:
        self.permission = permission

    async def __call__(self, event: TelegramObject, user: User, services: ServiceContainer) -> bool:
        return services.permissions.has_permission(user, self.permission)
