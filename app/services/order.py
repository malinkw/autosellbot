"""Служба заказов: покупка, смена статусов, возврат.

Покупка выполняется в одной транзакции: доступная позиция берётся с блокировкой
(``FOR UPDATE SKIP LOCKED``), затем списывается баланс (тоже с блокировкой строки
пользователя). Это исключает двойную продажу одной позиции и гонки по балансу.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessRuleError, NotFoundError
from app.models import Order, OrderStatusHistory, Product, User
from app.models.enums import OrderStatus, PositionStatus, TransactionType
from app.repositories.catalog import ProductRepository
from app.repositories.order import OrderRepository
from app.repositories.position import PositionRepository
from app.services.wallet import WalletService
from app.utils.ids import generate_number

# Разрешённые вручную переходы статусов (защита от некорректных изменений).
_TERMINAL = {OrderStatus.CANCELLED, OrderStatus.REFUNDED}


@dataclass(slots=True)
class PurchaseResult:
    """Результат успешной покупки."""

    order: Order
    content: str


class OrderService:
    """Бизнес-логика заказов."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._positions = PositionRepository(session)
        self._products = ProductRepository(session)
        self._wallet = WalletService(session)

    async def purchase(self, user: User, product_id: uuid.UUID) -> PurchaseResult:
        """Купить товар: зарезервировать позицию, списать баланс, выдать содержимое."""
        product = await self._products.get(product_id)
        if product is None or product.is_archived:
            raise NotFoundError("Товар недоступен.")

        position = await self._positions.lock_available(product_id)
        if position is None:
            raise BusinessRuleError("Товара нет в наличии.")

        amount = position.price_override or product.price

        order = await self._orders.create(
            number=generate_number("ORD"),
            user_id=user.id,
            product_id=product.id,
            position_id=position.id,
            amount=Decimal(amount),
            status=OrderStatus.CREATED,
        )
        await self._add_history(order, OrderStatus.CREATED, user, "Заказ создан")

        # Оплата балансом (может выбросить InsufficientFundsError — откат всей транзакции).
        await self._wallet.debit(
            user.id,
            Decimal(amount),
            type_=TransactionType.PURCHASE,
            reference=order.number,
            comment=f"Оплата заказа {order.number}",
        )

        # Выдача: позиция продана, заказ завершён.
        position.status = PositionStatus.SOLD
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.now(UTC)
        await self._add_history(order, OrderStatus.COMPLETED, user, "Оплачено, выдано")
        await self._session.flush()
        return PurchaseResult(order=order, content=position.content)

    async def get(self, order_id: uuid.UUID) -> Order:
        order = await self._orders.get(order_id)
        if order is None:
            raise NotFoundError("Заказ не найден.")
        return order

    async def get_by_number(self, number: str) -> Order:
        order = await self._orders.get_by_number(number)
        if order is None:
            raise NotFoundError("Заказ не найден.")
        return order

    async def history_for_user(self, user_id: uuid.UUID) -> list[Order]:
        """История заказов пользователя (бессрочно)."""
        return await self._orders.for_user(user_id)

    async def change_status(
        self,
        order_id: uuid.UUID,
        status: OrderStatus,
        *,
        actor: User,
        comment: str | None = None,
    ) -> Order:
        """Сменить статус заказа с записью в историю."""
        order = await self.get(order_id)
        if order.status in _TERMINAL:
            raise BusinessRuleError("Заказ в терминальном статусе изменить нельзя.")
        order.status = status
        if status == OrderStatus.COMPLETED and order.completed_at is None:
            order.completed_at = datetime.now(UTC)
        await self._add_history(order, status, actor, comment)
        await self._session.flush()
        return order

    async def refund(
        self, order_id: uuid.UUID, *, actor: User, comment: str | None = None
    ) -> Order:
        """Оформить возврат: вернуть средства и перевести заказ в статус «Возврат»."""
        order = await self.get(order_id)
        if order.status == OrderStatus.REFUNDED:
            raise BusinessRuleError("Возврат по заказу уже оформлен.")
        await self._wallet.credit(
            order.user_id,
            Decimal(order.amount),
            type_=TransactionType.REFUND,
            reference=order.number,
            comment=comment or f"Возврат по заказу {order.number}",
            created_by=actor,
        )
        order.status = OrderStatus.REFUNDED
        await self._add_history(order, OrderStatus.REFUNDED, actor, comment or "Возврат")
        await self._session.flush()
        return order

    async def _add_history(
        self,
        order: Order,
        status: OrderStatus,
        actor: User | None,
        comment: str | None,
    ) -> OrderStatusHistory:
        entry = OrderStatusHistory(
            order_id=order.id,
            status=status,
            changed_by_id=actor.id if actor else None,
            comment=comment,
        )
        self._session.add(entry)
        return entry

    async def get_product(self, product_id: uuid.UUID) -> Product:
        product = await self._products.get(product_id)
        if product is None:
            raise NotFoundError("Товар не найден.")
        return product
