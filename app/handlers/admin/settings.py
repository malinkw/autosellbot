"""Админ: настройки бота."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.states import SettingForm
from app.handlers.admin.common import edit
from app.keyboards.callbacks import AdminCB, MenuCB
from app.models import User
from app.permissions import Permission
from app.services import ServiceContainer

router = Router(name="admin_settings")
SECTION = "settings"


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def settings_list(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Список настроек бота."""
    services.permissions.require(user, Permission.SETTINGS_VIEW)
    items = await services.bot_settings.all()
    builder = InlineKeyboardBuilder()
    for item in items:
        value = item.value
        display = "🟢" if value is True else "🔴" if value is False else str(value)[:16]
        builder.button(
            text=f"{item.title}: {display}",
            callback_data=AdminCB(section=SECTION, action="edit", arg=item.key),
        )
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    await edit(callback, "⚙️ <b>Настройки</b>\nНажмите, чтобы изменить.", builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "edit")))
async def setting_edit(
    callback: CallbackQuery,
    callback_data: AdminCB,
    user: User,
    services: ServiceContainer,
    state: FSMContext,
) -> None:
    """Переключить булеву настройку или запросить новое текстовое значение."""
    services.permissions.require(user, Permission.SETTINGS_EDIT)
    key = callback_data.arg
    current = await services.bot_settings.get(key)
    if isinstance(current, bool):
        await services.bot_settings.set(key, not current)
        await services.audit.record(
            "settings.edit",
            actor=user,
            entity_type="setting",
            entity_id=key,
            new_data={"value": not current},
        )
        await settings_list(callback, user, services)
        return
    await state.set_state(SettingForm.value)
    await state.update_data(key=key)
    await callback.message.answer(f"Введите новое значение для «{key}» (текущее: {current}):")
    await callback.answer()


@router.message(SettingForm.value)
async def setting_save(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Сохранить новое значение настройки."""
    data = await state.get_data()
    await state.clear()
    services.permissions.require(user, Permission.SETTINGS_EDIT)
    key = data["key"]
    raw = (message.text or "").strip()
    current = await services.bot_settings.get(key)
    value: object = raw
    if isinstance(current, int) and not isinstance(current, bool):
        try:
            value = int(raw)
        except ValueError:
            await message.answer("Ожидалось число.")
            return
    await services.bot_settings.set(key, value)
    await services.audit.record(
        "settings.edit",
        actor=user,
        entity_type="setting",
        entity_id=key,
        new_data={"value": str(value)},
    )
    await message.answer("✅ Настройка сохранена.")
