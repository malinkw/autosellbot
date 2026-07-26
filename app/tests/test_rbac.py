"""Тесты RBAC: сервис прав и должностей."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.config import get_settings
from app.exceptions import BusinessRuleError, PermissionDeniedError
from app.permissions import Permission
from app.services.permission import PermissionService
from app.services.role import RoleService
from app.tests.conftest import make_user


async def test_owner_has_all_permissions(session) -> None:  # type: ignore[no-untyped-def]
    settings = get_settings()
    owner = await make_user(session, telegram_id=settings.bot.admin_ids[0])
    permissions = PermissionService(settings)
    assert permissions.is_owner(owner)
    assert permissions.has_permission(owner, Permission.USERS_BLOCK)
    permissions.require(owner, Permission.BACKUP_RESTORE)


async def test_user_without_role_denied(session) -> None:  # type: ignore[no-untyped-def]
    settings = get_settings()
    user = await make_user(session, telegram_id=500)
    permissions = PermissionService(settings)
    assert not permissions.has_permission(user, Permission.USERS_VIEW)
    with pytest.raises(PermissionDeniedError):
        permissions.require(user, Permission.USERS_VIEW)


async def test_role_permission_assignment(session) -> None:  # type: ignore[no-untyped-def]
    roles = RoleService(session)
    role = await roles.create("Модератор")
    await roles.set_permissions(
        role.id, [Permission.USERS_VIEW.value, Permission.USERS_BLOCK.value]
    )
    assert role.permission_codes == {Permission.USERS_VIEW.value, Permission.USERS_BLOCK.value}

    await roles.toggle_permission(role.id, Permission.USERS_BLOCK.value)
    assert Permission.USERS_BLOCK.value not in role.permission_codes


async def test_copy_permissions(session) -> None:  # type: ignore[no-untyped-def]
    roles = RoleService(session)
    source = await roles.create("Источник")
    target = await roles.create("Цель")
    await roles.set_permissions(
        source.id, [Permission.ORDERS_VIEW.value, Permission.ORDERS_REFUND.value]
    )
    await roles.copy_permissions(source.id, target.id)
    assert target.permission_codes == source.permission_codes


async def test_cannot_delete_system_role(session) -> None:  # type: ignore[no-untyped-def]
    roles = RoleService(session)
    owner_role = await roles.get((await roles.list_all())[0].id)
    with pytest.raises(BusinessRuleError):
        await roles.delete(owner_role.id)


async def test_staff_permission_check_via_role(session) -> None:  # type: ignore[no-untyped-def]
    settings = get_settings()
    roles = RoleService(session)
    role = await roles.create("Кассир")
    await roles.set_permissions(role.id, [Permission.TOPUPS_APPROVE.value])
    user = await make_user(session, telegram_id=600, balance=Decimal("0"))
    user.is_staff = True
    user.role_id = role.id
    await session.flush()
    await session.refresh(user)

    permissions = PermissionService(settings)
    assert permissions.has_permission(user, Permission.TOPUPS_APPROVE)
    assert not permissions.has_permission(user, Permission.TOPUPS_REJECT)
