"""Отзывы пользователя: выбор оценки и текста после завершения заказа."""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.states import ReviewFlow
from app.keyboards.callbacks import ReviewCB
from app.keyboards.user import rating_kb
from app.models import User
from app.services import ServiceContainer

router = Router(name="reviews")


@router.callback_query(ReviewCB.filter(F.action == "leave"))
async def leave_review(callback: CallbackQuery, callback_data: ReviewCB) -> None:
    """Предложить выбрать оценку."""
    await callback.message.answer(
        "⭐ Оцените заказ от 0 до 5:", reply_markup=rating_kb(callback_data.id)
    )
    await callback.answer()


@router.callback_query(ReviewCB.filter(F.action == "rate"))
async def choose_rating(
    callback: CallbackQuery, callback_data: ReviewCB, state: FSMContext
) -> None:
    """Сохранить оценку и запросить текст отзыва."""
    await state.set_state(ReviewFlow.text)
    await state.update_data(order_id=callback_data.id, rating=callback_data.value)
    await callback.message.answer("✍️ Напишите текст отзыва (или отправьте «-», чтобы пропустить):")
    await callback.answer()


@router.message(ReviewFlow.text)
async def submit_review(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Создать отзыв."""
    data = await state.get_data()
    await state.clear()
    order_id = uuid.UUID(data["order_id"])
    rating = int(data["rating"])
    text = (message.text or "").strip()
    review = await services.reviews.create(
        user, order_id, rating=rating, text=None if text in {"", "-"} else text
    )
    await services.audit.record(
        "review.create", actor=user, entity_type="review", entity_id=review.id
    )
    await message.answer("✅ Спасибо за отзыв!")

    from app.permissions import Permission

    staff = await services.users.staff_with_permission(Permission.REVIEWS_VIEW.value)
    await services.notifications.broadcast(staff, f"⭐ Новый отзыв с оценкой {rating}.")
