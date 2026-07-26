"""Админ: управление позициями выдачи."""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.states import PositionForm
from app.handlers.admin.common import edit
from app.keyboards.callbacks import AdminCB, MenuCB
from app.models import User
from app.models.enums import POSITION_STATUS_TITLES, PositionStatus
from app.permissions import Permission
from app.services import ServiceContainer

router = Router(name="admin_positions")
SECTION = "positions"


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def choose_product(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Выбрать товар для управления его позициями."""
    services.permissions.require(user, Permission.POSITIONS_VIEW)
    products = await services.catalog.all_products()
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(
            text=f"🛒 {product.name}",
            callback_data=AdminCB(section=SECTION, action="product", id=str(product.id)),
        )
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    await edit(callback, "📦 <b>Позиции</b>\nВыберите товар:", builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "product")))
async def product_positions(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Список позиций товара."""
    services.permissions.require(user, Permission.POSITIONS_VIEW)
    product_id = uuid.UUID(callback_data.id)
    positions = await services.positions.list_for_product(product_id)
    builder = InlineKeyboardBuilder()
    for pos in positions:
        title = POSITION_STATUS_TITLES[PositionStatus(pos.status)]
        builder.button(
            text=f"{title} · {pos.content[:20]}",
            callback_data=AdminCB(section=SECTION, action="view", id=str(pos.id)),
        )
    if services.permissions.has_permission(user, Permission.POSITIONS_CREATE):
        builder.button(
            text="➕ Добавить позицию",
            callback_data=AdminCB(section=SECTION, action="add", id=str(product_id)),
        )
    builder.button(text="⬅️ К товарам", callback_data=AdminCB(section=SECTION))
    builder.adjust(1)
    await edit(callback, "📦 Позиции товара:", builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "add")))
async def add_position(
    callback: CallbackQuery,
    callback_data: AdminCB,
    user: User,
    services: ServiceContainer,
    state: FSMContext,
) -> None:
    """Начать создание позиции."""
    services.permissions.require(user, Permission.POSITIONS_CREATE)
    await state.set_state(PositionForm.content)
    await state.update_data(product_id=callback_data.id)
    await callback.message.answer("Содержимое позиции (что получит покупатель):")
    await callback.answer()


@router.message(PositionForm.content)
async def save_position(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Создать позицию с автором."""
    services.permissions.require(user, Permission.POSITIONS_CREATE)
    data = await state.get_data()
    await state.clear()
    position = await services.positions.create(
        product_id=uuid.UUID(data["product_id"]),
        content=message.text or "",
        creator=user,
    )
    await services.audit.record(
        "position.create", actor=user, entity_type="position", entity_id=position.id
    )
    await message.answer("✅ Позиция создана.")


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "view")))
async def view_position(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Карточка позиции."""
    services.permissions.require(user, Permission.POSITIONS_VIEW)
    position = await services.positions.get(uuid.UUID(callback_data.id))
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🗄 Архив",
        callback_data=AdminCB(section=SECTION, action="archive", id=str(position.id)),
    )
    builder.button(
        text="🗑 Удалить",
        callback_data=AdminCB(section=SECTION, action="delete", id=str(position.id)),
    )
    builder.button(
        text="⬅️ К товару",
        callback_data=AdminCB(section=SECTION, action="product", id=str(position.product_id)),
    )
    builder.adjust(2, 1)
    title = POSITION_STATUS_TITLES[PositionStatus(position.status)]
    await edit(
        callback,
        f"📦 Позиция\nСтатус: {title}\nСодержимое: <code>{position.content}</code>",
        builder.as_markup(),
    )


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "archive")))
async def archive_position(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Архивировать позицию."""
    services.permissions.require(user, Permission.POSITIONS_ARCHIVE)
    position = await services.positions.archive(uuid.UUID(callback_data.id))
    await services.audit.record(
        "position.archive", actor=user, entity_type="position", entity_id=position.id
    )
    await view_position(callback, callback_data, user, services)


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "delete")))
async def delete_position(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Удалить позицию."""
    services.permissions.require(user, Permission.POSITIONS_DELETE)
    position = await services.positions.get(uuid.UUID(callback_data.id))
    product_id = position.product_id
    await services.positions.delete(position.id)
    await services.audit.record(
        "position.delete", actor=user, entity_type="position", entity_id=position.id
    )
    await callback.answer("Позиция удалена.", show_alert=True)
    callback_data = AdminCB(section=SECTION, action="product", id=str(product_id))
    await product_positions(callback, callback_data, user, services)
