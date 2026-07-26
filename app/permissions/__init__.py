"""Централизованная система разрешений (RBAC)."""

from app.permissions.registry import (
    ALL_PERMISSIONS,
    PERMISSION_METADATA,
    Permission,
    PermissionGroup,
    PermissionMeta,
    grouped_permissions,
)

__all__ = [
    "ALL_PERMISSIONS",
    "PERMISSION_METADATA",
    "Permission",
    "PermissionGroup",
    "PermissionMeta",
    "grouped_permissions",
]
