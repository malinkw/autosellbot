"""Кошелёк: баланс, история операций и заявки на пополнение (PDF-чек)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.states import TopUp
from app.keyboards.callbacks import MenuCB, WalletCB
from app.keyboards.user import wallet_kb
from app.models import User
from app.models.enums import (
    REQUISITE_TYPE_TITLES,
    TRANSACTION_TYPE_TITLES,
    RequisiteType,
    TransactionType,
)
from app.services import ServiceContainer
from app.utils.formatting import dt, money

router = Router(name="wallet")


async def _wallet_text(user: User, services: ServiceContainer) -> str:
    return f"💰 <b>Кошелёк</b>\nБаланс: <b>{money(user.balance)}</b>"


@router.callback_query(MenuCB.filter(F.action == "wallet"))
@router.callback_query(WalletCB.filter(F.action == "open"))
async def show_wallet(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Показать кошелёк."""
    requisites = await services.requisites.active()
    await callback.message.edit_text(
        await _wallet_text(user, services),
        reply_markup=wallet_kb(has_requisites=bool(requisites)),
    )
    await callback.answer()


@router.callback_query(WalletCB.filter(F.action == "history"))
async def show_history(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Показать историю операций."""
    transactions = await services.wallet.history(user.id, limit=20)
    if not transactions:
        await callback.answer("Операций пока нет.", show_alert=True)
        return
    lines = ["🧾 <b>История операций</b>", ""]
    for tx in transactions:
        title = TRANSACTION_TYPE_TITLES[TransactionType(tx.type)]
        sign = "＋" if tx.amount >= 0 else "－"
        lines.append(f"{dt(tx.created_at)} · {title}: {sign}{money(abs(tx.amount))}")
    requisites = await services.requisites.active()
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=wallet_kb(has_requisites=bool(requisites))
    )
    await callback.answer()


@router.callback_query(WalletCB.filter(F.action == "requisites"))
async def show_requisites(callback: CallbackQuery, services: ServiceContainer) -> None:
    """Показать активные платёжные реквизиты."""
    requisites = await services.requisites.active()
    if not requisites:
        await callback.answer("Реквизиты не заданы.", show_alert=True)
        return
    lines = ["💳 <b>Реквизиты для пополнения</b>", ""]
    for req in requisites:
        title = REQUISITE_TYPE_TITLES[RequisiteType(req.type)]
        holder = f" ({req.holder})" if req.holder else ""
        lines.append(f"{title}: <code>{req.value}</code>{holder}")
    await callback.message.edit_text("\n".join(lines), reply_markup=wallet_kb(has_requisites=True))
    await callback.answer()


@router.callback_query(WalletCB.filter(F.action == "topup"))
async def start_topup(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать заявку на пополнение."""
    await state.set_state(TopUp.amount)
    await callback.message.answer("💵 Введите сумму пополнения:")
    await callback.answer()


@router.message(TopUp.amount)
async def topup_amount(message: Message, state: FSMContext) -> None:
    """Принять сумму пополнения."""
    try:
        amount = Decimal((message.text or "").replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        await message.answer("Введите корректную сумму числом.")
        return
    if amount <= 0:
        await message.answer("Сумма должна быть больше нуля.")
        return
    await state.update_data(amount=str(amount))
    await state.set_state(TopUp.receipt)
    await message.answer("📎 Прикрепите PDF-чек об оплате (файл).")


@router.message(TopUp.receipt, F.document)
async def topup_receipt(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Принять PDF-чек и создать заявку."""
    document = message.document
    assert document is not None
    if (document.mime_type or "") != "application/pdf" and not (
        document.file_name or ""
    ).lower().endswith(".pdf"):
        await message.answer("Требуется файл в формате PDF. Прикрепите чек ещё раз.")
        return

    data = await state.get_data()
    await state.clear()
    amount = Decimal(data["amount"])
    min_amount = Decimal(str(await services.bot_settings.get("min_topup", 0)))
    max_amount = Decimal(str(await services.bot_settings.get("max_topup", 10**9)))

    request = await services.topups.create(
        user,
        amount,
        receipt_file_id=document.file_id,
        receipt_file_name=document.file_name,
        min_amount=min_amount,
        max_amount=max_amount,
    )
    await services.audit.record(
        "topup.created",
        actor=user,
        channel="payments",
        entity_type="topup",
        entity_id=request.id,
        new_data={"amount": str(amount)},
    )
    await message.answer(
        f"✅ Заявка <b>{request.number}</b> на {money(amount)} создана.\n"
        "Ожидайте подтверждения администратором."
    )

    from app.permissions import Permission

    staff = await services.users.staff_with_permission(Permission.TOPUPS_VIEW.value)
    await services.notifications.broadcast(
        staff, f"💳 Новая заявка на пополнение {request.number} — {money(amount)}."
    )


@router.message(TopUp.receipt)
async def topup_receipt_invalid(message: Message) -> None:
    """Напомнить, что нужен именно файл PDF."""
    await message.answer("Прикрепите PDF-чек файлом (документом).")
