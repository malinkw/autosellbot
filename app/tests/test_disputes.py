"""Тесты диспутов: окно открытия и авто-подбор участников."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.config import get_settings
from app.exceptions import BusinessRuleError, ConflictError
from app.models import Order
from app.models.enums import DisputeStatus
from app.services.dispute import DisputeService
from app.services.order import OrderService
from app.tests.conftest import add_position, make_product, make_user


async def _completed_order(session, buyer, seller) -> Order:  # type: ignore[no-untyped-def]
    product = await make_product(session, price=Decimal("100"))
    await add_position(session, product, seller, content="KEY")
    orders = OrderService(session)
    result = await orders.purchase(buyer, product.id)
    return result.order


async def test_open_dispute_within_window(session) -> None:  # type: ignore[no-untyped-def]
    buyer = await make_user(session, telegram_id=30, balance=Decimal("500"))
    seller = await make_user(session, telegram_id=31)
    order = await _completed_order(session, buyer, seller)

    disputes = DisputeService(session, get_settings())
    creation = await disputes.open(buyer, order.id, "Проблема с товаром")
    assert creation.dispute.status is DisputeStatus.OPEN
    # Создатель позиции — ответственный и участник.
    assert creation.dispute.responsible_id == seller.id
    assert any(u.id == seller.id for u in creation.participants)


async def test_open_dispute_after_window(session) -> None:  # type: ignore[no-untyped-def]
    buyer = await make_user(session, telegram_id=32, balance=Decimal("500"))
    seller = await make_user(session, telegram_id=33)
    order = await _completed_order(session, buyer, seller)
    order.completed_at = datetime.now(UTC) - timedelta(hours=48)
    await session.flush()

    disputes = DisputeService(session, get_settings())
    with pytest.raises(BusinessRuleError):
        await disputes.open(buyer, order.id, "Поздно")


async def test_duplicate_dispute_rejected(session) -> None:  # type: ignore[no-untyped-def]
    buyer = await make_user(session, telegram_id=34, balance=Decimal("500"))
    seller = await make_user(session, telegram_id=35)
    order = await _completed_order(session, buyer, seller)
    disputes = DisputeService(session, get_settings())
    await disputes.open(buyer, order.id, "Первый")
    with pytest.raises(ConflictError):
        await disputes.open(buyer, order.id, "Второй")


async def test_dispute_refund_returns_money(session) -> None:  # type: ignore[no-untyped-def]
    buyer = await make_user(session, telegram_id=36, balance=Decimal("500"))
    seller = await make_user(session, telegram_id=37)
    order = await _completed_order(session, buyer, seller)
    assert buyer.balance == Decimal("400.00")

    disputes = DisputeService(session, get_settings())
    creation = await disputes.open(buyer, order.id, "Возврат")
    await disputes.refund(creation.dispute.id, actor=seller)
    assert buyer.balance == Decimal("500.00")
