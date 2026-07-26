"""Админ: управление пользователями — поиск, просмотр, блокировки, баланс."""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.states import BalanceForm, SearchForm
from app.handlers.admin.common import edit
from app.keyboards.admin import section_back
from app.keyboards.callbacks import AdminCB, MenuCB
from app.models import User
from app.models.enums import AccountStatus
from app.permissions import Permission
from app.services import ServiceContainer
from app.utils.formatting import dt, money

router = Router(name="admin_users")
SECTION = "users"


def _user_card(target: User) -> str:
    status = "🟢 Активен" if target.status is AccountStatus.ACTIVE else "🔴 Заблокирован"
    return (
        f"<b>Пользователь {target.public_id}</b>\n"
        f"Ник: {target.nickname or '—'}\n"
        f"Username: @{target.username or '—'}\n"
        f"Баланс: <b>{money(target.balance)}</b>\n"
        f"Статус: {status}\n"
        f"Сотрудник: {'да' if target.is_staff else 'нет'}\n"
        f"Регистрация: {dt(target.created_at)}"
    )


def _user_kb(target: User) -> object:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="💰 Баланс",
        callback_data=AdminCB(section=SECTION, action="balance", id=str(target.id)),
    )
    if target.status is AccountStatus.ACTIVE:
        builder.button(
            text="🚫 Блок",
            callback_data=AdminCB(section=SECTION, action="block", id=str(target.id)),
        )
    else:
        builder.button(
            text="✅ Разблок",
            callback_data=AdminCB(section=SECTION, action="unblock", id=str(target.id)),
        )
    builder.button(text="🔍 Поиск", callback_data=AdminCB(section=SECTION, action="search"))
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(2, 2)
    return builder.as_markup()


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def open_users(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Раздел пользователей — приглашение к поиску."""
    services.permissions.require(user, Permission.USERS_VIEW)
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔍 Найти пользователя", callback_data=AdminCB(section=SECTION, action="search")
    )
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    await edit(
        callback, "👥 <b>Пользователи</b>\nНайдите по ID, нику или username.", builder.as_markup()
    )


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "search")))
async def ask_search(
    callback: CallbackQuery, user: User, services: ServiceContainer, state: FSMContext
) -> None:
    """Запросить поисковый запрос."""
    services.permissions.require(user, Permission.USERS_VIEW)
    await state.set_state(SearchForm.query)
    await state.update_data(scope=SECTION)
    await callback.message.answer("Введите ID, ник или username:")
    await callback.answer()


@router.message(SearchForm.query)
async def do_search(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Показать результаты поиска пользователей."""
    data = await state.get_data()
    if data.get("scope") != SECTION:
        return
    await state.clear()
    services.permissions.require(user, Permission.USERS_VIEW)
    results = await services.users.search(message.text or "")
    if not results:
        await message.answer("Ничего не найдено.", reply_markup=section_back(SECTION))
        return
    builder = InlineKeyboardBuilder()
    for target in results:
        builder.button(
            text=f"{target.public_id} · {target.nickname or '—'}",
            callback_data=AdminCB(section=SECTION, action="view", id=str(target.id)),
        )
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    await message.answer("Найдено:", reply_markup=builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "view")))
async def view_user(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Карточка пользователя."""
    services.permissions.require(user, Permission.USERS_VIEW_ONE)
    target = await services.users.get(uuid.UUID(callback_data.id))
    await edit(callback, _user_card(target), _user_kb(target))


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "block")))
async def block_user(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Заблокировать пользователя."""
    services.permissions.require(user, Permission.USERS_BLOCK)
    target = await services.users.get(uuid.UUID(callback_data.id))
    await services.users.block(target)
    await services.audit.record(
        "user.block", actor=user, channel="security", entity_type="user", entity_id=target.id
    )
    await edit(callback, _user_card(target), _user_kb(target))


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "unblock")))
async def unblock_user(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Разблокировать пользователя."""
    services.permissions.require(user, Permission.USERS_UNBLOCK)
    target = await services.users.get(uuid.UUID(callback_data.id))
    await services.users.unblock(target)
    await services.audit.record(
        "user.unblock", actor=user, channel="security", entity_type="user", entity_id=target.id
    )
    await edit(callback, _user_card(target), _user_kb(target))


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "balance")))
async def ask_balance(
    callback: CallbackQuery,
    callback_data: AdminCB,
    user: User,
    services: ServiceContainer,
    state: FSMContext,
) -> None:
    """Запросить сумму корректировки баланса."""
    services.permissions.require(user, Permission.USERS_EDIT_BALANCE)
    await state.set_state(BalanceForm.amount)
    await state.update_data(target_id=callback_data.id)
    await callback.message.answer("Введите сумму корректировки (например, 500 или -200):")
    await callback.answer()


@router.message(BalanceForm.amount)
async def balance_amount(message: Message, state: FSMContext) -> None:
    """Принять сумму корректировки."""
    try:
        amount = Decimal((message.text or "").replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        await message.answer("Введите корректное число.")
        return
    await state.update_data(amount=str(amount))
    await state.set_state(BalanceForm.comment)
    await message.answer("Комментарий к корректировке:")


@router.message(BalanceForm.comment)
async def balance_comment(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Применить корректировку баланса."""
    services.permissions.require(user, Permission.USERS_EDIT_BALANCE)
    data = await state.get_data()
    await state.clear()
    target_id = uuid.UUID(data["target_id"])
    amount = Decimal(data["amount"])
    tx = await services.wallet.manual_adjust(
        target_id, amount, admin=user, comment=message.text or "Корректировка"
    )
    await services.audit.record(
        "user.balance_adjust",
        actor=user,
        channel="payments",
        entity_type="user",
        entity_id=target_id,
        new_data={"amount": str(amount), "balance_after": str(tx.balance_after)},
    )
    target = await services.users.get(target_id)
    await services.notifications.notify_user(
        target, f"ℹ️ Ваш баланс изменён на {money(amount)} ({message.text})."
    )
    await message.answer(
        f"✅ Баланс обновлён: {money(tx.balance_after)}.", reply_markup=section_back(SECTION)
    )
