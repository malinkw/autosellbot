"""Общие клавиатуры: главное меню, пагинация, навигация."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.callbacks import MenuCB, PageCB


def main_menu(*, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Главное меню пользователя."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🛍 Каталог", callback_data=MenuCB(action="catalog"))
    builder.button(text="👤 Профиль", callback_data=MenuCB(action="profile"))
    builder.button(text="📦 Мои заказы", callback_data=MenuCB(action="orders"))
    builder.button(text="💰 Кошелёк", callback_data=MenuCB(action="wallet"))
    builder.button(text="⚖️ Диспуты", callback_data=MenuCB(action="disputes"))
    builder.button(text="ℹ️ Помощь", callback_data=MenuCB(action="help"))
    if is_admin:
        builder.button(text="🛠 Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()


def back_button(callback_data: str = MenuCB(action="home").pack()) -> InlineKeyboardMarkup:
    """Клавиатура с единственной кнопкой «Назад»."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data=callback_data)
    return builder.as_markup()


def pagination_row(
    builder: InlineKeyboardBuilder,
    *,
    scope: str,
    page: int,
    pages: int,
    ref: str = "",
) -> None:
    """Добавить строку пагинации (◀️ N/M ▶️) в существующий билдер."""
    if pages <= 1:
        return
    buttons: list[InlineKeyboardButton] = []
    if page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=PageCB(scope=scope, page=page - 1, ref=ref).pack(),
            )
        )
    buttons.append(InlineKeyboardButton(text=f"{page}/{pages}", callback_data="noop"))
    if page < pages:
        buttons.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=PageCB(scope=scope, page=page + 1, ref=ref).pack(),
            )
        )
    builder.row(*buttons)


def confirm_keyboard(action: str, entity_id: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия (Да/Нет)."""
    from app.keyboards.callbacks import ConfirmCB

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data=ConfirmCB(action=action, id=entity_id, yes=True))
    builder.button(text="❌ Нет", callback_data=ConfirmCB(action=action, id=entity_id, yes=False))
    return builder.as_markup()
