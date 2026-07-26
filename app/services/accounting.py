"""Служба бухгалтерии: агрегированные финансовые показатели."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, Transaction
from app.models.enums import TransactionType
from app.repositories.wallet import TransactionRepository

ZERO = Decimal("0.00")


@dataclass(slots=True)
class AccountingSummary:
    """Сводка по бухгалтерии."""

    total_profit: Decimal
    profit_day: Decimal
    profit_week: Decimal
    profit_month: Decimal
    profit_year: Decimal
    total_topups: Decimal
    total_refunds: Decimal
    total_payouts: Decimal
    operations_count: int
    orders_count: int
    average_check: Decimal


class AccountingService:
    """Расчёт финансовых показателей.

    Прибыль трактуется как разница между суммой покупок (списаний за заказы) и
    суммой возвратов за период.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tx = TransactionRepository(session)

    async def _profit_since(self, since: datetime | None) -> Decimal:
        purchases = await self._tx.sum_by_type(TransactionType.PURCHASE, since=since)
        refunds = await self._tx.sum_by_type(TransactionType.REFUND, since=since)
        return (purchases - refunds).quantize(Decimal("0.01"))

    async def summary(self) -> AccountingSummary:
        """Собрать полную сводку по бухгалтерии."""
        now = datetime.now(UTC)
        day = now - timedelta(days=1)
        week = now - timedelta(weeks=1)
        month = now - timedelta(days=30)
        year = now - timedelta(days=365)

        operations = int(
            (await self._session.execute(select(func.count(Transaction.id)))).scalar_one()
        )
        orders = int((await self._session.execute(select(func.count(Order.id)))).scalar_one())
        purchases_sum = await self._tx.sum_by_type(TransactionType.PURCHASE)
        average = (purchases_sum / orders).quantize(Decimal("0.01")) if orders else ZERO

        return AccountingSummary(
            total_profit=await self._profit_since(None),
            profit_day=await self._profit_since(day),
            profit_week=await self._profit_since(week),
            profit_month=await self._profit_since(month),
            profit_year=await self._profit_since(year),
            total_topups=await self._tx.sum_by_type(TransactionType.TOPUP),
            total_refunds=await self._tx.sum_by_type(TransactionType.REFUND),
            total_payouts=purchases_sum,
            operations_count=operations,
            orders_count=orders,
            average_check=average,
        )
