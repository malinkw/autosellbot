"""Навигация по главному меню: домой, профиль, вход в админ-панель."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.handlers.texts import profile_text
from app.keyboards.admin import admin_menu
from app.keyboards.callbacks import MenuCB
from app.keyboards.common import main_menu
from app.models import User
from app.services import ServiceContainer

router = Router(name="menu")


@router.callback_query(MenuCB.filter(F.action == "home"))
async def go_home(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Вернуться в главное меню."""
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=main_menu(is_admin=services.permissions.is_admin(user)),
    )
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "profile"))
async def show_profile(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Показать профиль пользователя."""
    stats = await services.users.profile_stats(user.id)
    await callback.message.edit_text(
        profile_text(user, stats),
        reply_markup=main_menu(is_admin=services.permissions.is_admin(user)),
    )
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "admin"))
async def open_admin(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Открыть административную панель (только при наличии доступа)."""
    if not services.permissions.is_admin(user):
        await callback.answer("Недостаточно прав.", show_alert=True)
        return
    permitted = services.permissions.permissions_of(user)
    await callback.message.edit_text(
        "🛠 <b>Административная панель</b>\nВыберите раздел:",
        reply_markup=admin_menu(permitted, is_owner=services.permissions.is_owner(user)),
    )
    await callback.answer()
