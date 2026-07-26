"""Админ: резервное копирование и восстановление базы."""

from __future__ import annotations

from pathlib import Path

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.handlers.admin.common import edit
from app.keyboards.callbacks import AdminCB, ConfirmCB, MenuCB
from app.models import User
from app.permissions import Permission
from app.services import ServiceContainer

router = Router(name="admin_backup")
SECTION = "backup"


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "open")))
async def backup_menu(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Меню резервного копирования."""
    services.permissions.require(user, Permission.BACKUP_CREATE)
    backups = services.backup.list_backups()
    lines = ["💾 <b>Резервные копии</b>", ""]
    (
        lines.extend(f"• {b.name}" for b in backups[:10])
        if backups
        else lines.append("Копий пока нет.")
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Создать копию", callback_data=AdminCB(section=SECTION, action="create"))
    if backups and services.permissions.has_permission(user, Permission.BACKUP_RESTORE):
        builder.button(
            text="♻️ Восстановить последнюю",
            callback_data=ConfirmCB(action="backup_restore", id=str(backups[0]), yes=True),
        )
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    await edit(callback, "\n".join(lines), builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == SECTION) & (F.action == "create")))
async def backup_create(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Создать резервную копию."""
    services.permissions.require(user, Permission.BACKUP_CREATE)
    await callback.answer("Создаю копию…")
    path = await services.backup.create()
    await services.audit.record("backup.create", actor=user, new_data={"path": str(path)})
    await callback.message.answer(f"✅ Копия создана: <code>{path.name}</code>")


@router.callback_query(ConfirmCB.filter((F.action == "backup_restore") & (F.yes.is_(True))))
async def backup_restore(
    callback: CallbackQuery, callback_data: ConfirmCB, user: User, services: ServiceContainer
) -> None:
    """Восстановить базу из последней копии."""
    services.permissions.require(user, Permission.BACKUP_RESTORE)
    await callback.answer("Восстанавливаю…")
    await services.backup.restore(Path(callback_data.id))
    await services.audit.record(
        "backup.restore", actor=user, channel="security", new_data={"path": callback_data.id}
    )
    await callback.message.answer("✅ База восстановлена из копии.")
