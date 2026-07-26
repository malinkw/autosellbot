"""Формирование текстовых сообщений интерфейса (вынесено для переиспользования)."""

from __future__ import annotations

from app.models import Dispute, Order, Product, User
from app.models.enums import (
    DISPUTE_STATUS_TITLES,
    ORDER_STATUS_TITLES,
    AccountStatus,
    DisputeStatus,
    OrderStatus,
)
from app.services.user import ProfileStats
from app.utils.formatting import dt, money, stars


def profile_text(user: User, stats: ProfileStats) -> str:
    """Текст профиля пользователя."""
    status = "🟢 Активен" if user.status is AccountStatus.ACTIVE else "🔴 Заблокирован"
    role = user.role.name if user.role else "—"
    lines = [
        "<b>👤 Профиль</b>",
        f"ID: <code>{user.public_id}</code>",
        f"Ник: <b>{user.nickname or '—'}</b>",
        f"Баланс: <b>{money(user.balance)}</b>",
        f"Заказов: {stats.orders_count}",
        f"Отзывов: {stats.reviews_count}",
        f"Регистрация: {dt(user.created_at)}",
        f"Статус: {status}",
    ]
    if user.is_staff:
        lines.append(f"Должность: {role}")
    return "\n".join(lines)


def product_card_text(product: Product, *, stock: int) -> str:
    """Текст карточки товара."""
    availability = f"✅ В наличии: {stock}" if stock > 0 else "❌ Нет в наличии"
    return "\n".join(
        [
            f"<b>{product.name}</b>",
            "",
            product.description or "Без описания",
            "",
            f"Цена: <b>{money(product.price)}</b>",
            f"Рейтинг: {stars(product.rating)} ({product.reviews_count})",
            availability,
        ]
    )


def order_text(order: Order) -> str:
    """Текст карточки заказа."""
    title = ORDER_STATUS_TITLES[OrderStatus(order.status)]
    return "\n".join(
        [
            f"<b>Заказ {order.number}</b>",
            f"Сумма: <b>{money(order.amount)}</b>",
            f"Статус: {title}",
            f"Создан: {dt(order.created_at)}",
            f"Завершён: {dt(order.completed_at)}",
        ]
    )


def dispute_text(dispute: Dispute) -> str:
    """Текст карточки диспута."""
    title = DISPUTE_STATUS_TITLES[DisputeStatus(dispute.status)]
    lines = [
        f"<b>Диспут {dispute.number}</b>",
        f"Статус: {title}",
        f"Тема: {dispute.subject}",
        f"Создан: {dt(dispute.created_at)}",
    ]
    if dispute.resolution:
        lines.append(f"Решение: {dispute.resolution}")
    return "\n".join(lines)
