"""Заказы пользователя: история и карточка заказа."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.handlers.texts import order_text
from app.keyboards.callbacks import MenuCB, OrderCB
from app.keyboards.user import order_view_kb, orders_kb
from app.models import Order, User
from app.models.enums import OrderStatus
from app.services import ServiceContainer

router = Router(name="orders")


@router.callback_query(MenuCB.filter(F.action == "orders"))
@router.callback_query(OrderCB.filter(F.action == "list"))
async def list_orders(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Показать историю заказов пользователя."""
    orders = await services.orders.history_for_user(user.id)
    if not orders:
        await callback.answer("У вас пока нет заказов.", show_alert=True)
        return
    await callback.message.edit_text("📦 <b>Мои заказы</b>", reply_markup=orders_kb(orders))
    await callback.answer()


async def _can_open_dispute(order: Order, services: ServiceContainer) -> bool:
    if order.status != OrderStatus.COMPLETED or order.completed_at is None:
        return False
    window = timedelta(hours=services.settings.app.dispute_window_hours)
    if datetime.now(UTC) - order.completed_at > window:
        return False
    return await services.disputes.get_for_order(order.id) is None


@router.callback_query(OrderCB.filter(F.action == "view"))
async def view_order(
    callback: CallbackQuery,
    callback_data: OrderCB,
    user: User,
    services: ServiceContainer,
) -> None:
    """Показать карточку заказа с доступными действиями."""
    order = await services.orders.get(uuid.UUID(callback_data.id))
    if order.user_id != user.id:
        await callback.answer("Заказ не найден.", show_alert=True)
        return

    can_dispute = await _can_open_dispute(order, services)
    can_review = (
        order.status == OrderStatus.COMPLETED
        and order.product_id is not None
        and await services.reviews.get_for_order(order.id) is None
    )
    await callback.message.edit_text(
        order_text(order),
        reply_markup=order_view_kb(order, can_dispute=can_dispute, can_review=can_review),
    )
    await callback.answer()
