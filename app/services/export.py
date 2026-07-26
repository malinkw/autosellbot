"""Служба экспорта отчётов (операции, заказы, бухгалтерия)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, Transaction
from app.models.enums import (
    ORDER_STATUS_TITLES,
    TRANSACTION_TYPE_TITLES,
    OrderStatus,
    TransactionType,
)
from app.repositories.order import OrderRepository
from app.repositories.wallet import TransactionRepository
from app.services.accounting import AccountingService
from app.utils.export import ExportFormat, render
from app.utils.formatting import dt


class ExportService:
    """Формирование выгрузок в CSV/XLSX/PDF."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = OrderRepository(session)
        self._tx = TransactionRepository(session)
        self._accounting = AccountingService(session)

    async def export_transactions(self, fmt: ExportFormat) -> tuple[bytes, str]:
        """Выгрузка всех операций."""
        rows_data = await self._tx.list(order_by=[Transaction.created_at.desc()])
        headers = ["Дата", "Тип", "Сумма", "Баланс после", "Ссылка", "Комментарий"]
        rows = [
            [
                dt(t.created_at),
                TRANSACTION_TYPE_TITLES[TransactionType(t.type)],
                str(t.amount),
                str(t.balance_after),
                t.reference or "",
                t.comment or "",
            ]
            for t in rows_data
        ]
        return render(fmt, headers, rows, title="Операции")

    async def export_orders(self, fmt: ExportFormat) -> tuple[bytes, str]:
        """Выгрузка всех заказов."""
        rows_data = await self._orders.list(order_by=[Order.created_at.desc()])
        headers = ["Номер", "Дата", "Сумма", "Статус", "Завершён"]
        rows = [
            [
                o.number,
                dt(o.created_at),
                str(o.amount),
                ORDER_STATUS_TITLES[OrderStatus(o.status)],
                dt(o.completed_at),
            ]
            for o in rows_data
        ]
        return render(fmt, headers, rows, title="Заказы")

    async def export_accounting(self, fmt: ExportFormat) -> tuple[bytes, str]:
        """Выгрузка сводки по бухгалтерии."""
        summary = await self._accounting.summary()
        headers = ["Показатель", "Значение"]
        rows = [
            ["Общая прибыль", str(summary.total_profit)],
            ["Прибыль за день", str(summary.profit_day)],
            ["Прибыль за неделю", str(summary.profit_week)],
            ["Прибыль за месяц", str(summary.profit_month)],
            ["Прибыль за год", str(summary.profit_year)],
            ["Сумма пополнений", str(summary.total_topups)],
            ["Сумма возвратов", str(summary.total_refunds)],
            ["Сумма выплат", str(summary.total_payouts)],
            ["Количество операций", str(summary.operations_count)],
            ["Количество заказов", str(summary.orders_count)],
            ["Средний чек", str(summary.average_check)],
        ]
        return render(fmt, headers, rows, title="Бухгалтерия")
