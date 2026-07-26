"""Централизованная служба проверки прав (сердце RBAC).

Каждое защищённое действие в системе обязано пройти через :meth:`PermissionService.require`.
Владельцы (Telegram ID из ``BOT__ADMIN_IDS``) обладают безусловными суперправами.
"""

from __future__ import annotations

from app.config import Settings
from app.exceptions import PermissionDeniedError
from app.logging import get_logger
from app.models import User
from app.permissions import Permission

log = get_logger("security")


class PermissionService:
    """Проверка и получение прав пользователя."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_owner(self, user: User) -> bool:
        """Является ли пользователь владельцем (безусловные суперправа)."""
        return user.telegram_id in self._settings.bot.admin_ids

    def permissions_of(self, user: User) -> set[str]:
        """Множество кодов прав пользователя (у владельца — все)."""
        if self.is_owner(user):
            return {p.value for p in Permission}
        if user.role is None:
            return set()
        return user.role.permission_codes

    def has_permission(self, user: User, permission: Permission) -> bool:
        """Есть ли у пользователя указанное право."""
        if self.is_owner(user):
            return True
        if user.role is None:
            return False
        return permission.value in user.role.permission_codes

    def has_any(self, user: User, *permissions: Permission) -> bool:
        """Есть ли у пользователя хотя бы одно из прав."""
        return any(self.has_permission(user, p) for p in permissions)

    def require(self, user: User, permission: Permission) -> None:
        """Проверить право; при отсутствии — выбросить :class:`PermissionDeniedError`."""
        if not self.has_permission(user, permission):
            log.warning(
                "permission_denied",
                user_id=str(user.id),
                telegram_id=user.telegram_id,
                permission=permission.value,
            )
            raise PermissionDeniedError(permission.value)

    def is_admin(self, user: User) -> bool:
        """Имеет ли пользователь доступ в админ-панель."""
        return self.is_owner(user) or self.has_permission(user, Permission.ADMIN_ACCESS)
