"""Клавиатуры пользовательской части (каталог, товар, кошелёк, диспуты)."""

from __future__ import annotations

from collections.abc import Sequence

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.callbacks import (
    CatalogCB,
    DisputeCB,
    MenuCB,
    OrderCB,
    ReviewCB,
    WalletCB,
)
from app.models import Category, Dispute, Order, Product
from app.models.enums import DISPUTE_STATUS_TITLES, ORDER_STATUS_TITLES, DisputeStatus, OrderStatus


def categories_kb(categories: Sequence[Category], *, parent_id: str = "") -> InlineKeyboardMarkup:
    """Список категорий/подкатегорий."""
    builder = InlineKeyboardBuilder()
    for category in categories:
        builder.button(
            text=f"📂 {category.name}",
            callback_data=CatalogCB(action="open", id=str(category.id)),
        )
    builder.button(text="🔍 Поиск товара", callback_data=CatalogCB(action="search"))
    builder.button(text="🏠 В меню", callback_data=MenuCB(action="home"))
    builder.adjust(1)
    return builder.as_markup()


def products_kb(products: Sequence[Product], *, back_id: str = "") -> InlineKeyboardMarkup:
    """Список товаров категории."""
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(
            text=f"🛒 {product.name}",
            callback_data=CatalogCB(action="product", id=str(product.id)),
        )
    builder.button(text="⬅️ Категории", callback_data=CatalogCB(action="root"))
    builder.adjust(1)
    return builder.as_markup()


def product_card_kb(product: Product, *, in_stock: bool) -> InlineKeyboardMarkup:
    """Карточка товара с кнопкой покупки."""
    builder = InlineKeyboardBuilder()
    if in_stock:
        builder.button(
            text="💳 Купить",
            callback_data=CatalogCB(action="buy", id=str(product.id)),
        )
    builder.button(text="⬅️ Назад", callback_data=CatalogCB(action="root"))
    builder.adjust(1)
    return builder.as_markup()


def orders_kb(orders: Sequence[Order]) -> InlineKeyboardMarkup:
    """Список заказов пользователя."""
    builder = InlineKeyboardBuilder()
    for order in orders:
        title = ORDER_STATUS_TITLES[OrderStatus(order.status)]
        builder.button(
            text=f"{order.number} · {title}",
            callback_data=OrderCB(action="view", id=str(order.id)),
        )
    builder.button(text="🏠 В меню", callback_data=MenuCB(action="home"))
    builder.adjust(1)
    return builder.as_markup()


def order_view_kb(order: Order, *, can_dispute: bool, can_review: bool) -> InlineKeyboardMarkup:
    """Действия по конкретному заказу."""
    builder = InlineKeyboardBuilder()
    if can_review:
        builder.button(
            text="⭐ Оставить отзыв",
            callback_data=ReviewCB(action="leave", id=str(order.id)),
        )
    if can_dispute:
        builder.button(
            text="⚖️ Открыть диспут",
            callback_data=DisputeCB(action="open", id=str(order.id)),
        )
    builder.button(text="⬅️ К заказам", callback_data=OrderCB(action="list"))
    builder.adjust(1)
    return builder.as_markup()


def rating_kb(order_id: str) -> InlineKeyboardMarkup:
    """Выбор оценки 0–5."""
    builder = InlineKeyboardBuilder()
    for value in range(6):
        builder.button(
            text=f"{value}⭐",
            callback_data=ReviewCB(action="rate", id=order_id, value=value),
        )
    builder.adjust(6)
    return builder.as_markup()


def wallet_kb(*, has_requisites: bool) -> InlineKeyboardMarkup:
    """Меню кошелька."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📥 Пополнить", callback_data=WalletCB(action="topup"))
    builder.button(text="🧾 История операций", callback_data=WalletCB(action="history"))
    if has_requisites:
        builder.button(text="💳 Реквизиты", callback_data=WalletCB(action="requisites"))
    builder.button(text="🏠 В меню", callback_data=MenuCB(action="home"))
    builder.adjust(1)
    return builder.as_markup()


def disputes_kb(disputes: Sequence[Dispute]) -> InlineKeyboardMarkup:
    """Список диспутов пользователя."""
    builder = InlineKeyboardBuilder()
    for dispute in disputes:
        title = DISPUTE_STATUS_TITLES[DisputeStatus(dispute.status)]
        builder.button(
            text=f"{dispute.number} · {title}",
            callback_data=DisputeCB(action="view", id=str(dispute.id)),
        )
    builder.button(text="🏠 В меню", callback_data=MenuCB(action="home"))
    builder.adjust(1)
    return builder.as_markup()


def dispute_view_kb(dispute: Dispute) -> InlineKeyboardMarkup:
    """Действия по диспуту для пользователя."""
    builder = InlineKeyboardBuilder()
    if dispute.status not in {DisputeStatus.CLOSED, DisputeStatus.REFUNDED}:
        builder.button(
            text="✍️ Ответить",
            callback_data=DisputeCB(action="reply", id=str(dispute.id)),
        )
    builder.button(
        text="🕓 История",
        callback_data=DisputeCB(action="history", id=str(dispute.id)),
    )
    builder.button(text="⬅️ К диспутам", callback_data=DisputeCB(action="list"))
    builder.adjust(1)
    return builder.as_markup()
