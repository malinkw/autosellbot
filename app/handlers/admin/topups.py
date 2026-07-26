"""Админ: заявки на пополнение — просмотр, подтверждение, отклонение."""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.handlers.admin.common import edit
from app.keyboards.admin import back_to_admin, section_back
from app.keyboards.callbacks import AdminCB
from app.models import User
from app.models.enums import TOPUP_STATUS_TITLES, TopUpStatus
from app.permissions import Permission
from app.services import ServiceContainer
from app.utils.formatting import dt, money

router = Router(name="admin_topups")
SECTION = "topups"


def _kb(request_id: str):  # type: ignore[no-untyped-def]
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ Подтвердить",
        callback_data=AdminCB(section=SECTION, action="approve", id=request_id),
    )
    builder.button(
        text="❌ Отклонить", callback_data=AdminCB(section=SECTION, action="reject", id=request_id)
    )
    builder.button(text="⬅️ К заявкам", callback_data=AdminCB(section=SECTION))
    builder.adjust(2, 1)
    return builder.as_markup()


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def list_topups(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Список ожидающих заявок."""
    services.permissions.require(user, Permission.TOPUPS_VIEW)
    pending = await services.topups.pending()
    if not pending:
        await edit(callback, "Нет заявок в ожидании.", back_to_admin())
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    from app.keyboards.callbacks import MenuCB

    builder = InlineKeyboardBuilder()
    for req in pending:
        builder.button(
            text=f"{req.number} · {money(req.amount)}",
            callback_data=AdminCB(section=SECTION, action="view", id=str(req.id)),
        )
    builder.button(text="⬅️ В админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    await edit(callback, "💳 <b>Заявки на пополнение</b>", builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "view")))
async def view_topup(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Карточка заявки с чеком."""
    services.permissions.require(user, Permission.TOPUPS_VIEW_ONE)
    request = await services.topups.get(uuid.UUID(callback_data.id))
    await services.topups.set_checking(request.id)
    applicant = await services.users.get(request.user_id)
    title = TOPUP_STATUS_TITLES[TopUpStatus(request.status)]
    text = (
        f"<b>Заявка {request.number}</b>\n"
        f"Пользователь: {applicant.public_id} ({applicant.nickname or '—'})\n"
        f"Сумма: <b>{money(request.amount)}</b>\n"
        f"Статус: {title}\n"
        f"Дата: {dt(request.created_at)}"
    )
    if request.receipt_file_id:
        await callback.message.answer_document(
            request.receipt_file_id, caption=text, reply_markup=_kb(str(request.id))
        )
        await callback.answer()
    else:
        await edit(callback, text + "\n\nЧек не приложен.", _kb(str(request.id)))


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "approve")))
async def approve_topup(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Подтвердить заявку и начислить баланс."""
    services.permissions.require(user, Permission.TOPUPS_APPROVE)
    request = await services.topups.approve(uuid.UUID(callback_data.id), admin=user)
    await services.audit.record(
        "topup.approve",
        actor=user,
        channel="payments",
        entity_type="topup",
        entity_id=request.id,
        new_data={"amount": str(request.amount)},
    )
    applicant = await services.users.get(request.user_id)
    await services.notifications.notify_user(
        applicant, f"✅ Пополнение {money(request.amount)} зачислено на баланс."
    )
    await callback.answer("Заявка подтверждена, баланс начислен.", show_alert=True)
    await callback.message.answer("✅ Готово.", reply_markup=section_back(SECTION))


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "reject")))
async def reject_topup(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Отклонить заявку."""
    services.permissions.require(user, Permission.TOPUPS_REJECT)
    request = await services.topups.reject(
        uuid.UUID(callback_data.id), admin=user, comment="Отклонено администратором"
    )
    await services.audit.record(
        "topup.reject", actor=user, channel="payments", entity_type="topup", entity_id=request.id
    )
    applicant = await services.users.get(request.user_id)
    await services.notifications.notify_user(applicant, f"❌ Заявка {request.number} отклонена.")
    await callback.answer("Заявка отклонена.", show_alert=True)
    await callback.message.answer("Отклонено.", reply_markup=section_back(SECTION))
