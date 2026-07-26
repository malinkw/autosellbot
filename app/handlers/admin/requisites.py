"""Админ: платёжные реквизиты."""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.states import RequisiteForm
from app.handlers.admin.common import edit
from app.keyboards.callbacks import AdminCB, MenuCB
from app.models import User
from app.models.enums import REQUISITE_TYPE_TITLES, RequisiteType
from app.permissions import Permission
from app.services import ServiceContainer

router = Router(name="admin_requisites")
SECTION = "requisites"


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def requisites_list(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Список реквизитов."""
    services.permissions.require(user, Permission.REQUISITES_VIEW)
    items = await services.requisites.all()
    builder = InlineKeyboardBuilder()
    for req in items:
        flag = "🟢" if req.is_active else "🔴"
        title = REQUISITE_TYPE_TITLES[RequisiteType(req.type)]
        builder.button(
            text=f"{flag} {title}: {req.value}",
            callback_data=AdminCB(section=SECTION, action="view", id=str(req.id)),
        )
    if services.permissions.has_permission(user, Permission.REQUISITES_CREATE):
        builder.button(
            text="➕ Карта", callback_data=AdminCB(section=SECTION, action="add", arg="card")
        )
        builder.button(
            text="➕ СБП", callback_data=AdminCB(section=SECTION, action="add", arg="sbp")
        )
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1, 2, 1)
    await edit(callback, "🏦 <b>Реквизиты</b>", builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "add")))
async def requisite_add(
    callback: CallbackQuery,
    callback_data: AdminCB,
    user: User,
    services: ServiceContainer,
    state: FSMContext,
) -> None:
    """Начать создание реквизита."""
    services.permissions.require(user, Permission.REQUISITES_CREATE)
    await state.set_state(RequisiteForm.value)
    await state.update_data(type=callback_data.arg)
    await callback.message.answer("Введите номер карты/СБП:")
    await callback.answer()


@router.message(RequisiteForm.value)
async def requisite_value(message: Message, state: FSMContext) -> None:
    """Принять значение реквизита."""
    await state.update_data(value=message.text or "")
    await state.set_state(RequisiteForm.holder)
    await message.answer("Держатель/название банка (или «-»):")


@router.message(RequisiteForm.holder)
async def requisite_finish(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Создать реквизит."""
    services.permissions.require(user, Permission.REQUISITES_CREATE)
    data = await state.get_data()
    await state.clear()
    holder = (message.text or "").strip()
    req = await services.requisites.create(
        type_=RequisiteType(data["type"]),
        value=data["value"],
        holder=None if holder in {"", "-"} else holder,
    )
    await services.audit.record(
        "requisite.create", actor=user, entity_type="requisite", entity_id=req.id
    )
    await message.answer("✅ Реквизит добавлен.")


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "view")))
async def requisite_view(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Карточка реквизита."""
    services.permissions.require(user, Permission.REQUISITES_VIEW)
    req = await services.requisites.get(uuid.UUID(callback_data.id))
    builder = InlineKeyboardBuilder()
    if req.is_active:
        builder.button(
            text="🔴 Отключить",
            callback_data=AdminCB(section=SECTION, action="disable", id=str(req.id)),
        )
    else:
        builder.button(
            text="🟢 Включить",
            callback_data=AdminCB(section=SECTION, action="enable", id=str(req.id)),
        )
    builder.button(
        text="🗑 Удалить", callback_data=AdminCB(section=SECTION, action="delete", id=str(req.id))
    )
    builder.button(text="⬅️ К реквизитам", callback_data=AdminCB(section=SECTION))
    builder.adjust(2, 1)
    title = REQUISITE_TYPE_TITLES[RequisiteType(req.type)]
    active = "да" if req.is_active else "нет"
    text = (
        f"🏦 {title}\nНомер: <code>{req.value}</code>\n"
        f"Держатель: {req.holder or '—'}\nАктивен: {active}"
    )
    await edit(callback, text, builder.as_markup())


@router.callback_query(
    AdminCB.filter((F.section == SECTION) & (F.action.in_({"enable", "disable"})))
)
async def requisite_toggle(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Включить/отключить реквизит."""
    enable = callback_data.action == "enable"
    services.permissions.require(
        user, Permission.REQUISITES_ENABLE if enable else Permission.REQUISITES_DISABLE
    )
    await services.requisites.set_active(uuid.UUID(callback_data.id), enable)
    await services.audit.record(
        f"requisite.{callback_data.action}",
        actor=user,
        entity_type="requisite",
        entity_id=callback_data.id,
    )
    await requisite_view(callback, callback_data, user, services)


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "delete")))
async def requisite_delete(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Удалить реквизит."""
    services.permissions.require(user, Permission.REQUISITES_DELETE)
    await services.requisites.delete(uuid.UUID(callback_data.id))
    await services.audit.record(
        "requisite.delete", actor=user, entity_type="requisite", entity_id=callback_data.id
    )
    await callback.answer("Реквизит удалён.", show_alert=True)
    await requisites_list(callback, user, services)
