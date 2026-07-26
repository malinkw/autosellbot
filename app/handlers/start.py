"""Старт, онбординг (выбор ника) и помощь."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.states import Onboarding
from app.exceptions import AppError
from app.keyboards.callbacks import MenuCB
from app.keyboards.common import main_menu
from app.models import User
from app.services import ServiceContainer

router = Router(name="start")


async def _show_menu(target: Message, user: User, services: ServiceContainer) -> None:
    welcome = await services.bot_settings.get("welcome_message", "Добро пожаловать!")
    await target.answer(
        f"{welcome}\n\nВыберите раздел:",
        reply_markup=main_menu(is_admin=services.permissions.is_admin(user)),
    )


@router.message(CommandStart())
async def cmd_start(
    message: Message, user: User, services: ServiceContainer, state: FSMContext
) -> None:
    """Обработка /start: онбординг для новых, меню — для остальных."""
    await state.clear()
    if not user.onboarded:
        await message.answer(
            "👋 Добро пожаловать! Давайте создадим профиль.\n\n"
            "Придумайте <b>ник</b> (3–20 символов: буквы, цифры, «_», «-»):"
        )
        await state.set_state(Onboarding.choosing_nickname)
        return
    await _show_menu(message, user, services)


@router.message(Onboarding.choosing_nickname)
async def process_nickname(
    message: Message, user: User, services: ServiceContainer, state: FSMContext
) -> None:
    """Установка выбранного ника с проверкой уникальности."""
    try:
        await services.users.set_nickname(user, message.text or "")
    except AppError as exc:
        await message.answer(f"⚠️ {exc.message}\nПопробуйте другой ник:")
        return
    await services.audit.record("user.onboarded", actor=user, entity_type="user", entity_id=user.id)
    await message.answer(f"✅ Профиль создан! Ваш ID: <code>{user.public_id}</code>")
    await _show_menu(message, user, services)


@router.message(Command("help"))
async def cmd_help(message: Message, services: ServiceContainer) -> None:
    """Показать справку и контакты поддержки."""
    faq = await services.bot_settings.get("faq", "Справка недоступна.")
    support = await services.bot_settings.get("support_contacts", "—")
    await message.answer(f"<b>ℹ️ Помощь</b>\n\n{faq}\n\nПоддержка: {support}")


@router.callback_query(MenuCB.filter(F.action == "help"))
async def menu_help(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Справка из меню."""
    faq = await services.bot_settings.get("faq", "Справка недоступна.")
    support = await services.bot_settings.get("support_contacts", "—")
    await callback.message.edit_text(
        f"<b>ℹ️ Помощь</b>\n\n{faq}\n\nПоддержка: {support}",
        reply_markup=main_menu(is_admin=services.permissions.is_admin(user)),
    )
    await callback.answer()
