"""Админ: общая статистика."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.handlers.admin.common import edit
from app.keyboards.admin import back_to_admin
from app.keyboards.callbacks import AdminCB
from app.models import User
from app.permissions import Permission
from app.services import ServiceContainer
from app.utils.formatting import money
from app.utils.pagination import Paginator

router = Router(name="admin_stats")
SECTION = "stats"


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def stats_view(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Показать общую статистику магазина."""
    services.permissions.require(user, Permission.STATS_VIEW)
    users_total = (await services.users.paginate(Paginator(page=1, page_size=1))).total
    staff_total = len(await services.staff.list_all())
    disputes_total = len(await services.disputes.all_disputes())
    summary = await services.accounting.summary()
    text = (
        "📈 <b>Статистика</b>\n\n"
        f"Пользователей: {users_total}\n"
        f"Сотрудников: {staff_total}\n"
        f"Заказов: {summary.orders_count}\n"
        f"Операций: {summary.operations_count}\n"
        f"Диспутов: {disputes_total}\n"
        f"Общая прибыль: {money(summary.total_profit)}\n"
        f"Средний чек: {money(summary.average_check)}"
    )
    await edit(callback, text, back_to_admin())
