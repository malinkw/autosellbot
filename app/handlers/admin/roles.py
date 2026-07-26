"""Админ: должности и права (RBAC-редактор)."""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app.bot.states import RoleForm
from app.handlers.admin.common import edit
from app.keyboards.admin import (
    permission_editor_kb,
    role_view_kb,
    roles_kb,
    section_back,
)
from app.keyboards.callbacks import AdminCB
from app.models import User
from app.permissions import Permission, PermissionGroup
from app.services import ServiceContainer

router = Router(name="admin_roles")
SECTION = "roles"


def _role_card(role) -> str:  # type: ignore[no-untyped-def]
    return (
        f"<b>Должность: {role.name}</b>\n"
        f"Описание: {role.description or '—'}\n"
        f"Прав назначено: {len(role.permissions)} / {len(list(Permission))}\n"
        f"Системная: {'да' if role.is_system else 'нет'}"
    )


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def list_roles(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Список должностей."""
    services.permissions.require(user, Permission.ROLES_VIEW)
    roles = await services.roles.list_all()
    can_create = services.permissions.has_permission(user, Permission.ROLES_CREATE)
    await edit(callback, "🎚 <b>Должности</b>", roles_kb(roles, can_create=can_create))


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "view")))
async def view_role(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Карточка должности."""
    services.permissions.require(user, Permission.ROLES_VIEW)
    role = await services.roles.get(uuid.UUID(callback_data.id))
    await edit(
        callback,
        _role_card(role),
        role_view_kb(
            role,
            can_edit_perms=services.permissions.has_permission(
                user, Permission.ROLES_ASSIGN_PERMISSIONS
            ),
            can_delete=services.permissions.has_permission(user, Permission.ROLES_DELETE),
        ),
    )


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "create")))
async def create_role_start(
    callback: CallbackQuery, user: User, services: ServiceContainer, state: FSMContext
) -> None:
    """Начать создание должности."""
    services.permissions.require(user, Permission.ROLES_CREATE)
    await state.set_state(RoleForm.name)
    await callback.message.answer("Введите название новой должности:")
    await callback.answer()


@router.message(RoleForm.name)
async def create_role_finish(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Создать должность."""
    services.permissions.require(user, Permission.ROLES_CREATE)
    await state.clear()
    role = await services.roles.create(message.text or "")
    await services.audit.record("role.create", actor=user, entity_type="role", entity_id=role.id)
    await message.answer(f"✅ Должность «{role.name}» создана.", reply_markup=section_back(SECTION))


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "perms")))
async def edit_permissions(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Редактор прав должности (по группам)."""
    services.permissions.require(user, Permission.ROLES_ASSIGN_PERMISSIONS)
    role = await services.roles.get(uuid.UUID(callback_data.id))
    group = PermissionGroup[callback_data.arg] if callback_data.arg else next(iter(PermissionGroup))
    text = (
        f"🔧 Права должности «{role.name}»\nГруппа: <b>{group}</b>\n"
        "Нажмите, чтобы переключить право:"
    )
    await edit(callback, text, permission_editor_kb(role, group))


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "toggle")))
async def toggle_permission(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Переключить одно право должности."""
    services.permissions.require(user, Permission.ROLES_ASSIGN_PERMISSIONS)
    role = await services.roles.toggle_permission(uuid.UUID(callback_data.id), callback_data.arg)
    await services.audit.record(
        "role.toggle_permission",
        actor=user,
        channel="security",
        entity_type="role",
        entity_id=role.id,
        new_data={"permission": callback_data.arg},
    )
    from app.permissions import PERMISSION_METADATA

    try:
        meta_group = PERMISSION_METADATA[Permission(callback_data.arg)].group
    except ValueError:
        meta_group = next(iter(PermissionGroup))
    await edit(
        callback,
        f"🔧 Права должности «{role.name}»\nГруппа: <b>{meta_group}</b>",
        permission_editor_kb(role, meta_group),
    )


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "delete")))
async def delete_role(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Удалить должность."""
    services.permissions.require(user, Permission.ROLES_DELETE)
    await services.roles.delete(uuid.UUID(callback_data.id))
    await services.audit.record(
        "role.delete", actor=user, entity_type="role", entity_id=callback_data.id
    )
    await callback.answer("Должность удалена.", show_alert=True)
    roles = await services.roles.list_all()
    await edit(callback, "🎚 <b>Должности</b>", roles_kb(roles, can_create=True))


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "export_perms")))
async def export_permissions(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Экспортировать права должности в JSON-файл."""
    services.permissions.require(user, Permission.ROLES_EXPORT_PERMISSIONS)
    import json

    role = await services.roles.get(uuid.UUID(callback_data.id))
    codes = await services.roles.export_permissions(role.id)
    payload = json.dumps({"role": role.name, "permissions": codes}, ensure_ascii=False, indent=2)
    file = BufferedInputFile(payload.encode("utf-8"), filename=f"role_{role.name}_permissions.json")
    await callback.message.answer_document(file, caption=f"Экспорт прав должности «{role.name}».")
    await callback.answer()
