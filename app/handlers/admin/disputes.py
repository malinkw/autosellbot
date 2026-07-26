"""Админ: обработка диспутов (ответ, статус, закрытие, возврат, переоткрытие)."""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.states import DisputeReplyAdmin
from app.handlers.admin.common import edit
from app.keyboards.callbacks import AdminCB, MenuCB
from app.models import User
from app.models.enums import DISPUTE_STATUS_TITLES, DisputeStatus
from app.permissions import Permission
from app.services import ServiceContainer
from app.utils.formatting import dt

router = Router(name="admin_disputes")
SECTION = "disputes"


def _dispute_kb(dispute, user: User, services: ServiceContainer):  # type: ignore[no-untyped-def]
    builder = InlineKeyboardBuilder()
    did = str(dispute.id)
    if services.permissions.has_permission(user, Permission.DISPUTES_REPLY):
        builder.button(
            text="✍️ Ответить", callback_data=AdminCB(section=SECTION, action="reply", id=did)
        )
    if services.permissions.has_permission(user, Permission.DISPUTES_CHANGE_STATUS):
        builder.button(
            text="🔄 В работу",
            callback_data=AdminCB(
                section=SECTION, action="status", id=did, arg=DisputeStatus.IN_REVIEW.value
            ),
        )
    if services.permissions.has_permission(user, Permission.DISPUTES_REFUND):
        builder.button(
            text="💸 Возврат", callback_data=AdminCB(section=SECTION, action="refund", id=did)
        )
    if services.permissions.has_permission(user, Permission.DISPUTES_CLOSE):
        builder.button(
            text="✅ Закрыть", callback_data=AdminCB(section=SECTION, action="close", id=did)
        )
    if services.permissions.has_permission(user, Permission.DISPUTES_REOPEN):
        builder.button(
            text="♻️ Переоткрыть", callback_data=AdminCB(section=SECTION, action="reopen", id=did)
        )
    builder.button(
        text="🕓 История", callback_data=AdminCB(section=SECTION, action="history", id=did)
    )
    builder.button(text="⬅️ К диспутам", callback_data=AdminCB(section=SECTION))
    builder.adjust(2)
    return builder.as_markup()


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def disputes_list(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Список всех диспутов."""
    services.permissions.require(user, Permission.DISPUTES_VIEW)
    disputes = await services.disputes.all_disputes()
    builder = InlineKeyboardBuilder()
    for d in disputes:
        title = DISPUTE_STATUS_TITLES[DisputeStatus(d.status)]
        builder.button(
            text=f"{d.number} · {title}",
            callback_data=AdminCB(section=SECTION, action="view", id=str(d.id)),
        )
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    await edit(callback, "⚖️ <b>Диспуты</b>", builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "view")))
async def dispute_view(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Карточка диспута с участниками."""
    services.permissions.require(user, Permission.DISPUTES_VIEW_ONE)
    dispute = await services.disputes.get(uuid.UUID(callback_data.id))
    title = DISPUTE_STATUS_TITLES[DisputeStatus(dispute.status)]
    participants = ", ".join(p.user.public_id for p in dispute.participants) or "—"
    text = (
        f"<b>Диспут {dispute.number}</b>\nСтатус: {title}\n"
        f"Тема: {dispute.subject}\nУчастники: {participants}\n"
        f"Создан: {dt(dispute.created_at)}"
    )
    await edit(callback, text, _dispute_kb(dispute, user, services))


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "reply")))
async def dispute_reply_start(
    callback: CallbackQuery,
    callback_data: AdminCB,
    user: User,
    services: ServiceContainer,
    state: FSMContext,
) -> None:
    """Начать ответ в диспуте."""
    services.permissions.require(user, Permission.DISPUTES_REPLY)
    await state.set_state(DisputeReplyAdmin.message)
    await state.update_data(dispute_id=callback_data.id)
    await callback.message.answer("Введите ответ:")
    await callback.answer()


@router.message(DisputeReplyAdmin.message)
async def dispute_reply_admin(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Ответ сотрудника в диспуте."""
    data = await state.get_data()
    await state.clear()
    services.permissions.require(user, Permission.DISPUTES_REPLY)
    dispute_id = uuid.UUID(data["dispute_id"])
    await services.disputes.reply(dispute_id, user, text=message.text, file_id=None)
    dispute = await services.disputes.get(dispute_id)
    opener = await services.users.get(dispute.opener_id)
    await services.notifications.notify_user(opener, f"⚖️ Новый ответ по диспуту {dispute.number}.")
    await message.answer("✅ Ответ отправлен.")


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "status")))
async def dispute_status(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Изменить статус диспута."""
    services.permissions.require(user, Permission.DISPUTES_CHANGE_STATUS)
    await services.disputes.change_status(
        uuid.UUID(callback_data.id), DisputeStatus(callback_data.arg), actor=user
    )
    await services.audit.record(
        "dispute.status", actor=user, entity_type="dispute", entity_id=callback_data.id
    )
    await dispute_view(callback, callback_data, user, services)


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "refund")))
async def dispute_refund(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Оформить возврат по диспуту."""
    services.permissions.require(user, Permission.DISPUTES_REFUND)
    dispute = await services.disputes.refund(uuid.UUID(callback_data.id), actor=user)
    await services.audit.record(
        "dispute.refund",
        actor=user,
        channel="payments",
        entity_type="dispute",
        entity_id=dispute.id,
    )
    opener = await services.users.get(dispute.opener_id)
    await services.notifications.notify_user(
        opener, f"💸 По диспуту {dispute.number} оформлен возврат."
    )
    await callback.answer("Возврат оформлен.", show_alert=True)
    await dispute_view(callback, callback_data, user, services)


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "close")))
async def dispute_close(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Закрыть диспут."""
    services.permissions.require(user, Permission.DISPUTES_CLOSE)
    dispute = await services.disputes.close(
        uuid.UUID(callback_data.id), actor=user, resolution="Закрыт администратором"
    )
    await services.audit.record(
        "dispute.close", actor=user, entity_type="dispute", entity_id=dispute.id
    )
    opener = await services.users.get(dispute.opener_id)
    await services.notifications.notify_user(opener, f"⚖️ Диспут {dispute.number} закрыт.")
    await dispute_view(callback, callback_data, user, services)


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "reopen")))
async def dispute_reopen(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Повторно открыть диспут."""
    services.permissions.require(user, Permission.DISPUTES_REOPEN)
    await services.disputes.reopen(uuid.UUID(callback_data.id), actor=user)
    await services.audit.record(
        "dispute.reopen", actor=user, entity_type="dispute", entity_id=callback_data.id
    )
    await dispute_view(callback, callback_data, user, services)


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "history")))
async def dispute_history(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """История диспута."""
    services.permissions.require(user, Permission.DISPUTES_VIEW_ONE)
    history = await services.disputes.history(uuid.UUID(callback_data.id))
    lines = ["🕓 <b>История диспута</b>", ""]
    for e in history:
        lines.append(f"{dt(e.created_at)} · {e.action}: {e.details or ''}")
    await callback.message.answer("\n".join(lines))
    await callback.answer()
