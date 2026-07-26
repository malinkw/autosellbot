"""Админ: модерация отзывов."""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.states import ReviewReplyForm
from app.handlers.admin.common import edit
from app.keyboards.callbacks import AdminCB, MenuCB
from app.models import User
from app.permissions import Permission
from app.services import ServiceContainer
from app.utils.formatting import dt, stars

router = Router(name="admin_reviews")
SECTION = "reviews"


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def reviews_list(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Список последних отзывов."""
    services.permissions.require(user, Permission.REVIEWS_VIEW)
    reviews = await services.reviews.recent()
    builder = InlineKeyboardBuilder()
    for review in reviews:
        flag = "🙈" if review.is_hidden else "⭐"
        builder.button(
            text=f"{flag} {stars(review.rating)} · {dt(review.created_at)}",
            callback_data=AdminCB(section=SECTION, action="view", id=str(review.id)),
        )
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    await edit(callback, "⭐ <b>Отзывы</b>", builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "view")))
async def review_view(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Карточка отзыва."""
    services.permissions.require(user, Permission.REVIEWS_VIEW)
    review = await services.reviews.get(uuid.UUID(callback_data.id))
    builder = InlineKeyboardBuilder()
    if services.permissions.has_permission(user, Permission.REVIEWS_REPLY):
        builder.button(
            text="✍️ Ответить",
            callback_data=AdminCB(section=SECTION, action="reply", id=str(review.id)),
        )
    if services.permissions.has_permission(user, Permission.REVIEWS_HIDE):
        builder.button(
            text=("👁 Показать" if review.is_hidden else "🙈 Скрыть"),
            callback_data=AdminCB(section=SECTION, action="hide", id=str(review.id)),
        )
    if services.permissions.has_permission(user, Permission.REVIEWS_DELETE):
        builder.button(
            text="🗑 Удалить",
            callback_data=AdminCB(section=SECTION, action="delete", id=str(review.id)),
        )
    builder.button(text="⬅️ К отзывам", callback_data=AdminCB(section=SECTION))
    builder.adjust(2, 1)
    text = (
        f"⭐ Отзыв {stars(review.rating)}\n\n{review.text or 'Без текста'}\n\n"
        f"Ответ: {review.admin_reply or '—'}\nСкрыт: {'да' if review.is_hidden else 'нет'}"
    )
    await edit(callback, text, builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "hide")))
async def review_hide(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Скрыть/показать отзыв."""
    services.permissions.require(user, Permission.REVIEWS_HIDE)
    review = await services.reviews.get(uuid.UUID(callback_data.id))
    await services.reviews.set_hidden(review.id, not review.is_hidden)
    await services.audit.record(
        "review.hide", actor=user, entity_type="review", entity_id=review.id
    )
    await review_view(callback, callback_data, user, services)


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "delete")))
async def review_delete(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Удалить отзыв."""
    services.permissions.require(user, Permission.REVIEWS_DELETE)
    await services.reviews.delete(uuid.UUID(callback_data.id))
    await services.audit.record(
        "review.delete", actor=user, entity_type="review", entity_id=callback_data.id
    )
    await callback.answer("Отзыв удалён.", show_alert=True)
    await reviews_list(callback, user, services)


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "reply")))
async def review_reply_start(
    callback: CallbackQuery,
    callback_data: AdminCB,
    user: User,
    services: ServiceContainer,
    state: FSMContext,
) -> None:
    """Начать ответ на отзыв."""
    services.permissions.require(user, Permission.REVIEWS_REPLY)
    await state.set_state(ReviewReplyForm.text)
    await state.update_data(review_id=callback_data.id)
    await callback.message.answer("Введите ответ на отзыв:")
    await callback.answer()


@router.message(ReviewReplyForm.text)
async def review_reply_finish(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Сохранить ответ на отзыв."""
    data = await state.get_data()
    await state.clear()
    services.permissions.require(user, Permission.REVIEWS_REPLY)
    review = await services.reviews.reply(uuid.UUID(data["review_id"]), user, message.text or "")
    await services.audit.record(
        "review.reply", actor=user, entity_type="review", entity_id=review.id
    )
    reviewer = await services.users.get(review.user_id)
    await services.notifications.notify_user(reviewer, "💬 На ваш отзыв ответила администрация.")
    await message.answer("✅ Ответ сохранён.")
