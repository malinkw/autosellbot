"""Тесты оформления заказов."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.exceptions import BusinessRuleError, InsufficientFundsError
from app.models.enums import OrderStatus, PositionStatus
from app.repositories.position import PositionRepository
from app.services.order import OrderService
from app.tests.conftest import add_position, make_product, make_user


async def test_purchase_flow(session) -> None:  # type: ignore[no-untyped-def]
    user = await make_user(session, telegram_id=20, balance=Decimal("500"))
    product = await make_product(session, price=Decimal("100"))
    await add_position(session, product, user, content="KEY-123")

    orders = OrderService(session)
    result = await orders.purchase(user, product.id)

    assert result.content == "KEY-123"
    assert result.order.status is OrderStatus.COMPLETED
    assert result.order.completed_at is not None
    assert user.balance == Decimal("400.00")
    assert result.order.position_id is not None
    position = await PositionRepository(session).get(result.order.position_id)
    assert position is not None
    assert position.status is PositionStatus.SOLD


async def test_purchase_without_stock(session) -> None:  # type: ignore[no-untyped-def]
    user = await make_user(session, telegram_id=21, balance=Decimal("500"))
    product = await make_product(session, price=Decimal("100"))
    orders = OrderService(session)
    with pytest.raises(BusinessRuleError):
        await orders.purchase(user, product.id)


async def test_purchase_insufficient_funds_keeps_position(session) -> None:  # type: ignore[no-untyped-def]
    buyer = await make_user(session, telegram_id=22, balance=Decimal("50"))
    seller = await make_user(session, telegram_id=23)
    product = await make_product(session, price=Decimal("100"))
    await add_position(session, product, seller, content="KEY-999")

    orders = OrderService(session)
    with pytest.raises(InsufficientFundsError):
        await orders.purchase(buyer, product.id)


async def test_refund_returns_funds(session) -> None:  # type: ignore[no-untyped-def]
    user = await make_user(session, telegram_id=24, balance=Decimal("300"))
    product = await make_product(session, price=Decimal("100"))
    await add_position(session, product, user, content="KEY-1")
    orders = OrderService(session)
    result = await orders.purchase(user, product.id)
    assert user.balance == Decimal("200.00")

    refunded = await orders.refund(result.order.id, actor=user)
    assert refunded.status is OrderStatus.REFUNDED
    assert user.balance == Decimal("300.00")
