"""Клавиатуры административной панели."""

from __future__ import annotations

from collections.abc import Sequence

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.callbacks import AdminCB, MenuCB
from app.models import Role
from app.permissions import (
    PERMISSION_METADATA,
    Permission,
    PermissionGroup,
    grouped_permissions,
)

# Разделы админ-панели: (раздел, подпись, право доступа к разделу).
ADMIN_SECTIONS: list[tuple[str, str, Permission]] = [
    ("users", "👥 Пользователи", Permission.USERS_VIEW),
    ("catalog", "🛍 Товары", Permission.PRODUCTS_VIEW),
    ("categories", "📂 Категории", Permission.CATEGORIES_VIEW),
    ("positions", "📦 Позиции", Permission.POSITIONS_VIEW),
    ("locality", "🗺 Местность", Permission.DISTRICTS_VIEW),
    ("staff", "🧑‍💼 Сотрудники", Permission.STAFF_VIEW),
    ("roles", "🎚 Должности", Permission.ROLES_VIEW),
    ("topups", "💳 Заявки", Permission.TOPUPS_VIEW),
    ("disputes", "⚖️ Диспуты", Permission.DISPUTES_VIEW),
    ("reviews", "⭐ Отзывы", Permission.REVIEWS_VIEW),
    ("accounting", "📊 Бухгалтерия", Permission.ACCOUNTING_VIEW),
    ("requisites", "🏦 Реквизиты", Permission.REQUISITES_VIEW),
    ("settings", "⚙️ Настройки", Permission.SETTINGS_VIEW),
    ("logs", "📜 Логи", Permission.LOGS_VIEW),
    ("stats", "📈 Статистика", Permission.STATS_VIEW),
    ("backup", "💾 Бэкапы", Permission.BACKUP_CREATE),
]


def admin_menu(permitted: set[str], *, is_owner: bool) -> InlineKeyboardMarkup:
    """Главное меню админ-панели — только доступные пользователю разделы."""
    builder = InlineKeyboardBuilder()
    for section, title, permission in ADMIN_SECTIONS:
        if is_owner or permission.value in permitted:
            builder.button(text=title, callback_data=AdminCB(section=section))
    builder.button(text="🏠 В меню", callback_data=MenuCB(action="home"))
    builder.adjust(2)
    return builder.as_markup()


def back_to_admin() -> InlineKeyboardMarkup:
    """Кнопка возврата в админ-меню."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ В админ-панель", callback_data=MenuCB(action="admin"))
    return builder.as_markup()


def section_back(section: str) -> InlineKeyboardMarkup:
    """Кнопка возврата в раздел админ-панели."""
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data=AdminCB(section=section))
    builder.button(text="🛠 Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    return builder.as_markup()


def export_formats(section: str) -> InlineKeyboardMarkup:
    """Выбор формата экспорта."""
    builder = InlineKeyboardBuilder()
    for fmt in ("csv", "xlsx", "pdf"):
        builder.button(
            text=fmt.upper(),
            callback_data=AdminCB(section=section, action="export", arg=fmt),
        )
    builder.button(text="⬅️ Назад", callback_data=AdminCB(section=section))
    builder.adjust(3, 1)
    return builder.as_markup()


def roles_kb(roles: Sequence[Role], *, can_create: bool) -> InlineKeyboardMarkup:
    """Список должностей."""
    builder = InlineKeyboardBuilder()
    for role in roles:
        builder.button(
            text=f"🎚 {role.name} ({len(role.permissions)})",
            callback_data=AdminCB(section="roles", action="view", id=str(role.id)),
        )
    if can_create:
        builder.button(
            text="➕ Создать должность",
            callback_data=AdminCB(section="roles", action="create"),
        )
    builder.button(text="⬅️ Назад", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    return builder.as_markup()


def role_view_kb(role: Role, *, can_edit_perms: bool, can_delete: bool) -> InlineKeyboardMarkup:
    """Действия с должностью."""
    builder = InlineKeyboardBuilder()
    if can_edit_perms:
        builder.button(
            text="🔧 Права",
            callback_data=AdminCB(section="roles", action="perms", id=str(role.id)),
        )
        builder.button(
            text="📤 Экспорт прав",
            callback_data=AdminCB(section="roles", action="export_perms", id=str(role.id)),
        )
    if can_delete and not role.is_system:
        builder.button(
            text="🗑 Удалить",
            callback_data=AdminCB(section="roles", action="delete", id=str(role.id)),
        )
    builder.button(text="⬅️ К должностям", callback_data=AdminCB(section="roles"))
    builder.adjust(2, 1)
    return builder.as_markup()


def permission_editor_kb(role: Role, group: PermissionGroup) -> InlineKeyboardMarkup:
    """Редактор прав должности по группам (переключение отдельного права)."""
    builder = InlineKeyboardBuilder()
    granted = role.permission_codes
    groups = list(grouped_permissions().keys())

    # Переключатели прав текущей группы.
    for meta in grouped_permissions()[group]:
        mark = "✅" if meta.permission.value in granted else "⬜️"
        builder.button(
            text=f"{mark} {meta.title}",
            callback_data=AdminCB(
                section="roles",
                action="toggle",
                id=str(role.id),
                arg=meta.permission.value,
            ),
        )
    builder.adjust(1)

    # Переключение между группами.
    nav = InlineKeyboardBuilder()
    idx = groups.index(group)
    prev_group = groups[idx - 1]
    next_group = groups[(idx + 1) % len(groups)]
    nav.button(
        text="◀️ Группа",
        callback_data=AdminCB(
            section="roles", action="perms", id=str(role.id), arg=prev_group.name
        ),
    )
    nav.button(
        text="Группа ▶️",
        callback_data=AdminCB(
            section="roles", action="perms", id=str(role.id), arg=next_group.name
        ),
    )
    nav.button(
        text="⬅️ К должности",
        callback_data=AdminCB(section="roles", action="view", id=str(role.id)),
    )
    nav.adjust(2, 1)
    builder.attach(nav)
    return builder.as_markup()


def permission_group_title(group: PermissionGroup) -> str:
    """Человекочитаемое имя группы прав."""
    return str(group)


def entity_actions_kb(
    section: str,
    entity_id: str,
    actions: Sequence[tuple[str, str]],
    *,
    back: str | None = None,
) -> InlineKeyboardMarkup:
    """Универсальная клавиатура действий над сущностью.

    :param actions: последовательность ``(action_code, подпись)``.
    """
    builder = InlineKeyboardBuilder()
    for action, title in actions:
        builder.button(
            text=title,
            callback_data=AdminCB(section=section, action=action, id=entity_id),
        )
    builder.button(
        text="⬅️ Назад",
        callback_data=AdminCB(section=section, action=back or "open"),
    )
    builder.adjust(1)
    return builder.as_markup()


def all_permission_titles() -> dict[str, str]:
    """Словарь код → название права (для отображения)."""
    return {p.value: PERMISSION_METADATA[p].title for p in Permission}
