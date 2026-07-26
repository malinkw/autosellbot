"""Админ: бухгалтерия и экспорт отчётов."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.handlers.admin.common import edit
from app.keyboards.callbacks import AdminCB, MenuCB
from app.models import User
from app.permissions import Permission
from app.services import ServiceContainer
from app.utils.export import ExportFormat
from app.utils.formatting import money

router = Router(name="admin_accounting")
SECTION = "accounting"


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def accounting_summary(
    callback: CallbackQuery, user: User, services: ServiceContainer
) -> None:
    """Сводка по бухгалтерии."""
    services.permissions.require(user, Permission.ACCOUNTING_VIEW)
    s = await services.accounting.summary()
    text = (
        "📊 <b>Бухгалтерия</b>\n\n"
        f"Общая прибыль: <b>{money(s.total_profit)}</b>\n"
        f"За день: {money(s.profit_day)}\n"
        f"За неделю: {money(s.profit_week)}\n"
        f"За месяц: {money(s.profit_month)}\n"
        f"За год: {money(s.profit_year)}\n\n"
        f"Пополнения: {money(s.total_topups)}\n"
        f"Возвраты: {money(s.total_refunds)}\n"
        f"Выплаты: {money(s.total_payouts)}\n"
        f"Операций: {s.operations_count}\n"
        f"Заказов: {s.orders_count}\n"
        f"Средний чек: {money(s.average_check)}"
    )
    builder = InlineKeyboardBuilder()
    if services.permissions.has_permission(user, Permission.ACCOUNTING_EXPORT):
        for fmt in ("csv", "xlsx", "pdf"):
            builder.button(
                text=f"⬇️ {fmt.upper()}",
                callback_data=AdminCB(section=SECTION, action="export", arg=fmt),
            )
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(3, 1)
    await edit(callback, text, builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "export")))
async def accounting_export(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Экспортировать сводку в выбранном формате."""
    services.permissions.require(user, Permission.ACCOUNTING_EXPORT)
    content, filename = await services.export.export_accounting(ExportFormat(callback_data.arg))
    await services.audit.record(
        "accounting.export", actor=user, new_data={"format": callback_data.arg}
    )
    await callback.message.answer_document(BufferedInputFile(content, filename=filename))
    await callback.answer("Готово.")
