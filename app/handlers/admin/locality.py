"""Админ: управление местностью (районы и локации)."""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.states import DistrictForm, LocationForm
from app.handlers.admin.common import edit
from app.keyboards.callbacks import AdminCB, MenuCB
from app.models import User
from app.permissions import Permission
from app.services import ServiceContainer

router = Router(name="admin_locality")
SECTION = "locality"


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def locality_menu(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Меню местности."""
    services.permissions.require(user, Permission.DISTRICTS_VIEW)
    builder = InlineKeyboardBuilder()
    builder.button(text="🏘 Районы", callback_data=AdminCB(section=SECTION, action="districts"))
    builder.button(text="📍 Локации", callback_data=AdminCB(section=SECTION, action="locations"))
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(2, 1)
    await edit(callback, "🗺 <b>Местность</b>", builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "districts")))
async def districts_list(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Список районов."""
    services.permissions.require(user, Permission.DISTRICTS_VIEW)
    districts = await services.locality.list_districts()
    builder = InlineKeyboardBuilder()
    for d in districts:
        builder.button(
            text=f"🏘 {d.name}",
            callback_data=AdminCB(section=SECTION, action="district_del", id=str(d.id)),
        )
    if services.permissions.has_permission(user, Permission.DISTRICTS_CREATE):
        builder.button(
            text="➕ Создать район", callback_data=AdminCB(section=SECTION, action="district_add")
        )
    builder.button(text="⬅️ Назад", callback_data=AdminCB(section=SECTION))
    builder.adjust(1)
    await edit(callback, "🏘 <b>Районы</b>\n(нажмите на район, чтобы удалить)", builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "district_add")))
async def district_add(
    callback: CallbackQuery, user: User, services: ServiceContainer, state: FSMContext
) -> None:
    """Начать создание района."""
    services.permissions.require(user, Permission.DISTRICTS_CREATE)
    await state.set_state(DistrictForm.name)
    await callback.message.answer("Название района:")
    await callback.answer()


@router.message(DistrictForm.name)
async def district_save(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Создать район."""
    services.permissions.require(user, Permission.DISTRICTS_CREATE)
    await state.clear()
    district = await services.locality.create_district(message.text or "")
    await services.audit.record(
        "district.create", actor=user, entity_type="district", entity_id=district.id
    )
    await message.answer(f"✅ Район «{district.name}» создан.")


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "district_del")))
async def district_delete(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Удалить район."""
    services.permissions.require(user, Permission.DISTRICTS_DELETE)
    await services.locality.delete_district(uuid.UUID(callback_data.id))
    await services.audit.record(
        "district.delete", actor=user, entity_type="district", entity_id=callback_data.id
    )
    await callback.answer("Район удалён.", show_alert=True)
    await districts_list(callback, user, services)


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "locations")))
async def locations_list(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Список локаций."""
    services.permissions.require(user, Permission.LOCATIONS_VIEW)
    locations = await services.locality.list_locations()
    builder = InlineKeyboardBuilder()
    for loc in locations:
        builder.button(
            text=f"📍 {loc.name}",
            callback_data=AdminCB(section=SECTION, action="location_del", id=str(loc.id)),
        )
    if services.permissions.has_permission(user, Permission.LOCATIONS_CREATE):
        builder.button(
            text="➕ Создать локацию", callback_data=AdminCB(section=SECTION, action="location_add")
        )
    builder.button(text="⬅️ Назад", callback_data=AdminCB(section=SECTION))
    builder.adjust(1)
    await edit(
        callback, "📍 <b>Локации</b>\n(нажмите на локацию, чтобы удалить)", builder.as_markup()
    )


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "location_add")))
async def location_add(
    callback: CallbackQuery, user: User, services: ServiceContainer, state: FSMContext
) -> None:
    """Начать создание локации."""
    services.permissions.require(user, Permission.LOCATIONS_CREATE)
    await state.set_state(LocationForm.name)
    await callback.message.answer("Название локации:")
    await callback.answer()


@router.message(LocationForm.name)
async def location_save(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Создать локацию."""
    services.permissions.require(user, Permission.LOCATIONS_CREATE)
    await state.clear()
    location = await services.locality.create_location(message.text or "")
    await services.audit.record(
        "location.create", actor=user, entity_type="location", entity_id=location.id
    )
    await message.answer(f"✅ Локация «{location.name}» создана.")


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "location_del")))
async def location_delete(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Удалить локацию."""
    services.permissions.require(user, Permission.LOCATIONS_DELETE)
    await services.locality.delete_location(uuid.UUID(callback_data.id))
    await services.audit.record(
        "location.delete", actor=user, entity_type="location", entity_id=callback_data.id
    )
    await callback.answer("Локация удалена.", show_alert=True)
    await locations_list(callback, user, services)
