"""Админ: просмотр и очистка журнала аудита."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.handlers.admin.common import edit
from app.keyboards.callbacks import AdminCB, ConfirmCB, MenuCB
from app.models import User
from app.permissions import Permission
from app.services import ServiceContainer
from app.utils.formatting import dt

router = Router(name="admin_logs")
SECTION = "logs"


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def logs_view(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Показать последние записи аудита."""
    services.permissions.require(user, Permission.LOGS_VIEW)
    from app.utils.pagination import Paginator

    page = await services.audit.list_all(Paginator(page=1, page_size=20))
    lines = ["📜 <b>Журнал аудита</b> (последние)", ""]
    for entry in page.items:
        actor = entry.actor_telegram_id or "system"
        lines.append(f"{dt(entry.created_at)} · {actor} · {entry.action} · {entry.result}")
    builder = InlineKeyboardBuilder()
    if services.permissions.has_permission(user, Permission.LOGS_DELETE):
        builder.button(
            text="🧹 Очистить журнал", callback_data=ConfirmCB(action="logs_purge", yes=True)
        )
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    await edit(callback, "\n".join(lines) if page.items else "Журнал пуст.", builder.as_markup())


@router.callback_query(ConfirmCB.filter((F.action == "logs_purge") & (F.yes.is_(True))))
async def logs_purge(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Очистить журнал аудита."""
    services.permissions.require(user, Permission.LOGS_DELETE)
    count = await services.audit.purge()
    await callback.answer(f"Удалено записей: {count}", show_alert=True)
    await logs_view(callback, user, services)
