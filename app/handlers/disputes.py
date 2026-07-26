"""Диспуты пользователя: открытие, переписка, история."""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.states import DisputeOpen, DisputeReply
from app.handlers.texts import dispute_text
from app.keyboards.callbacks import DisputeCB, MenuCB
from app.keyboards.user import dispute_view_kb, disputes_kb
from app.models import User
from app.services import ServiceContainer
from app.utils.formatting import dt

router = Router(name="disputes")


@router.callback_query(MenuCB.filter(F.action == "disputes"))
@router.callback_query(DisputeCB.filter(F.action == "list"))
async def list_disputes(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Список диспутов пользователя."""
    disputes = await services.disputes.for_opener(user.id)
    if not disputes:
        await callback.answer("У вас нет диспутов.", show_alert=True)
        return
    await callback.message.edit_text("⚖️ <b>Мои диспуты</b>", reply_markup=disputes_kb(disputes))
    await callback.answer()


@router.callback_query(DisputeCB.filter(F.action == "open"))
async def dispute_open_start(
    callback: CallbackQuery, callback_data: DisputeCB, state: FSMContext
) -> None:
    """Начать открытие диспута по заказу."""
    await state.set_state(DisputeOpen.subject)
    await state.update_data(order_id=callback_data.id)
    await callback.message.answer("✍️ Опишите проблему по заказу:")
    await callback.answer()


@router.message(DisputeOpen.subject)
async def dispute_open_finish(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Создать диспут и уведомить автоматически подобранных участников."""
    data = await state.get_data()
    await state.clear()
    order_id = uuid.UUID(data["order_id"])
    creation = await services.disputes.open(user, order_id, message.text or "")
    await services.audit.record(
        "dispute.open",
        actor=user,
        entity_type="dispute",
        entity_id=creation.dispute.id,
    )
    await message.answer(
        f"✅ Диспут <b>{creation.dispute.number}</b> открыт.\n"
        "Сотрудники уведомлены, ожидайте ответа."
    )
    await services.notifications.broadcast(
        creation.participants,
        f"⚖️ Новый диспут {creation.dispute.number} по заказу.",
    )


@router.callback_query(DisputeCB.filter(F.action == "view"))
async def view_dispute(
    callback: CallbackQuery,
    callback_data: DisputeCB,
    user: User,
    services: ServiceContainer,
) -> None:
    """Показать карточку диспута."""
    dispute = await services.disputes.get(uuid.UUID(callback_data.id))
    if dispute.opener_id != user.id and not services.permissions.is_admin(user):
        await callback.answer("Диспут не найден.", show_alert=True)
        return
    await callback.message.edit_text(dispute_text(dispute), reply_markup=dispute_view_kb(dispute))
    await callback.answer()


@router.callback_query(DisputeCB.filter(F.action == "reply"))
async def dispute_reply_start(
    callback: CallbackQuery, callback_data: DisputeCB, state: FSMContext
) -> None:
    """Начать ответ в диспуте."""
    await state.set_state(DisputeReply.message)
    await state.update_data(dispute_id=callback_data.id)
    await callback.message.answer("✍️ Введите сообщение (можно приложить фото):")
    await callback.answer()


@router.message(DisputeReply.message)
async def dispute_reply_finish(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Добавить сообщение в диспут."""
    data = await state.get_data()
    await state.clear()
    dispute_id = uuid.UUID(data["dispute_id"])
    file_id = (
        message.photo[-1].file_id
        if message.photo
        else (message.document.file_id if message.document else None)
    )
    await services.disputes.reply(
        dispute_id, user, text=message.text or message.caption, file_id=file_id
    )
    await message.answer("✅ Сообщение отправлено.")


@router.callback_query(DisputeCB.filter(F.action == "history"))
async def dispute_history(
    callback: CallbackQuery, callback_data: DisputeCB, services: ServiceContainer
) -> None:
    """Показать историю диспута."""
    dispute_id = uuid.UUID(callback_data.id)
    history = await services.disputes.history(dispute_id)
    lines = ["🕓 <b>История диспута</b>", ""]
    for entry in history:
        lines.append(f"{dt(entry.created_at)} · {entry.action}: {entry.details or ''}")
    await callback.message.answer("\n".join(lines))
    await callback.answer()
