"""Админ: управление сотрудниками."""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.states import StaffForm
from app.handlers.admin.common import edit
from app.keyboards.callbacks import AdminCB, MenuCB
from app.models import User
from app.models.enums import AccountStatus
from app.permissions import Permission
from app.services import ServiceContainer

router = Router(name="admin_staff")
SECTION = "staff"


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def staff_list(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Список сотрудников."""
    services.permissions.require(user, Permission.STAFF_VIEW)
    staff = await services.staff.list_all()
    builder = InlineKeyboardBuilder()
    for member in staff:
        role = member.role.name if member.role else "—"
        builder.button(
            text=f"🧑‍💼 {member.public_id} · {role}",
            callback_data=AdminCB(section=SECTION, action="view", id=str(member.id)),
        )
    if services.permissions.has_permission(user, Permission.STAFF_INVITE):
        builder.button(
            text="➕ Пригласить", callback_data=AdminCB(section=SECTION, action="invite")
        )
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    await edit(callback, "🧑‍💼 <b>Сотрудники</b>", builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "invite")))
async def invite_start(
    callback: CallbackQuery, user: User, services: ServiceContainer, state: FSMContext
) -> None:
    """Начать приглашение сотрудника."""
    services.permissions.require(user, Permission.STAFF_INVITE)
    await state.set_state(StaffForm.username)
    await callback.message.answer("Введите @username пользователя (он должен был запускать бота):")
    await callback.answer()


@router.message(StaffForm.username)
async def invite_username(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Принять username и предложить должность."""
    services.permissions.require(user, Permission.STAFF_INVITE)
    await state.update_data(username=(message.text or "").strip())
    roles = await services.roles.list_all()
    builder = InlineKeyboardBuilder()
    for role in roles:
        builder.button(
            text=role.name,
            callback_data=AdminCB(section=SECTION, action="invite_role", arg=str(role.id)),
        )
    builder.adjust(1)
    await state.set_state(StaffForm.role)
    await message.answer("Выберите должность:", reply_markup=builder.as_markup())


@router.callback_query(
    StaffForm.role, AdminCB.filter((F.section == SECTION) & (F.action == "invite_role"))
)
async def invite_finish(
    callback: CallbackQuery,
    callback_data: AdminCB,
    state: FSMContext,
    user: User,
    services: ServiceContainer,
) -> None:
    """Назначить пользователя сотрудником."""
    services.permissions.require(user, Permission.STAFF_INVITE)
    data = await state.get_data()
    await state.clear()
    member = await services.staff.invite(data["username"], uuid.UUID(callback_data.arg))
    await services.audit.record(
        "staff.invite", actor=user, channel="security", entity_type="user", entity_id=member.id
    )
    await services.notifications.notify_user(member, "🎉 Вам назначена должность сотрудника.")
    await callback.message.answer(f"✅ {member.public_id} назначен сотрудником.")
    await callback.answer()


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "view")))
async def staff_view(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Карточка сотрудника со статистикой."""
    services.permissions.require(user, Permission.STAFF_VIEW)
    member = await services.users.get(uuid.UUID(callback_data.id))
    stats = await services.staff.stats(member.id)
    builder = InlineKeyboardBuilder()
    if member.status is AccountStatus.ACTIVE:
        builder.button(
            text="🚫 Блок",
            callback_data=AdminCB(section=SECTION, action="block", id=str(member.id)),
        )
    else:
        builder.button(
            text="✅ Разблок",
            callback_data=AdminCB(section=SECTION, action="unblock", id=str(member.id)),
        )
    builder.button(
        text="🗑 Уволить",
        callback_data=AdminCB(section=SECTION, action="dismiss", id=str(member.id)),
    )
    builder.button(text="⬅️ К сотрудникам", callback_data=AdminCB(section=SECTION))
    builder.adjust(2, 1)
    text = (
        f"🧑‍💼 <b>{member.public_id}</b>\n"
        f"Должность: {member.role.name if member.role else '—'}\n"
        f"Создано позиций: {stats.positions_created}\n"
        f"Активность: {stats.last_activity}\n"
        f"Статус: {'активен' if member.status is AccountStatus.ACTIVE else 'заблокирован'}"
    )
    await edit(callback, text, builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "block")))
async def staff_block(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Заблокировать сотрудника."""
    services.permissions.require(user, Permission.STAFF_BLOCK)
    await services.staff.block(uuid.UUID(callback_data.id))
    await services.audit.record(
        "staff.block",
        actor=user,
        channel="security",
        entity_type="user",
        entity_id=callback_data.id,
    )
    await staff_view(callback, callback_data, user, services)


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "unblock")))
async def staff_unblock(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Разблокировать сотрудника."""
    services.permissions.require(user, Permission.STAFF_UNBLOCK)
    await services.staff.unblock(uuid.UUID(callback_data.id))
    await services.audit.record(
        "staff.unblock",
        actor=user,
        channel="security",
        entity_type="user",
        entity_id=callback_data.id,
    )
    await staff_view(callback, callback_data, user, services)


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "dismiss")))
async def staff_dismiss(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Уволить сотрудника."""
    services.permissions.require(user, Permission.STAFF_DISMISS)
    await services.staff.dismiss(uuid.UUID(callback_data.id))
    await services.audit.record(
        "staff.dismiss",
        actor=user,
        channel="security",
        entity_type="user",
        entity_id=callback_data.id,
    )
    await callback.answer("Сотрудник уволен.", show_alert=True)
    await staff_list(callback, user, services)
