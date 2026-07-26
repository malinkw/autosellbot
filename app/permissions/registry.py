"""Реестр разрешений RBAC — единый источник правды.

Ключевое требование ТЗ: **каждое** действие в системе защищено отдельным правом.
Никакие два действия не объединяются в одно право. Любая новая функция обязана
добавить сюда новый член :class:`Permission` — это единственное место, где
объявляются права, и оно же используется для сидинга таблицы ``permissions``.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum


class PermissionGroup(StrEnum):
    """Группы прав для отображения в административной панели."""

    ADMIN = "Админ-панель"
    USERS = "Пользователи"
    ORDERS = "Заказы"
    PRODUCTS = "Товары"
    CATEGORIES = "Категории"
    POSITIONS = "Позиции"
    LOCALITY = "Местность"
    STAFF = "Сотрудники"
    ROLES = "Должности"
    ACCOUNTING = "Бухгалтерия"
    REQUISITES = "Реквизиты"
    TOPUPS = "Заявки на пополнение"
    DISPUTES = "Диспуты"
    REVIEWS = "Отзывы"
    SETTINGS = "Настройки"
    LOGS = "Логи"
    SYSTEM = "Система"


class Permission(StrEnum):
    """Полный перечень атомарных прав системы.

    Значение члена — стабильный машинный код права (хранится в БД).
    """

    # --- Админ-панель -------------------------------------------------------
    ADMIN_ACCESS = "admin.access"

    # --- Пользователи -------------------------------------------------------
    USERS_VIEW = "users.view"
    USERS_VIEW_ONE = "users.view_one"
    USERS_EDIT = "users.edit"
    USERS_EDIT_BALANCE = "users.edit_balance"
    USERS_BLOCK = "users.block"
    USERS_UNBLOCK = "users.unblock"
    USERS_VIEW_ORDERS = "users.view_orders"
    USERS_VIEW_TRANSACTIONS = "users.view_transactions"
    USERS_VIEW_REVIEWS = "users.view_reviews"
    USERS_VIEW_DISPUTES = "users.view_disputes"

    # --- Заказы -------------------------------------------------------------
    ORDERS_VIEW = "orders.view"
    ORDERS_VIEW_ONE = "orders.view_one"
    ORDERS_EDIT = "orders.edit"
    ORDERS_DELETE = "orders.delete"
    ORDERS_CHANGE_STATUS = "orders.change_status"
    ORDERS_REFUND = "orders.refund"

    # --- Товары -------------------------------------------------------------
    PRODUCTS_VIEW = "products.view"
    PRODUCTS_CREATE = "products.create"
    PRODUCTS_EDIT = "products.edit"
    PRODUCTS_DELETE = "products.delete"
    PRODUCTS_ARCHIVE = "products.archive"
    PRODUCTS_HIDE = "products.hide"
    PRODUCTS_CHANGE_PRICE = "products.change_price"
    PRODUCTS_CHANGE_DESCRIPTION = "products.change_description"
    PRODUCTS_CHANGE_PHOTOS = "products.change_photos"
    PRODUCTS_CHANGE_CATEGORY = "products.change_category"
    PRODUCTS_CHANGE_SUBCATEGORY = "products.change_subcategory"
    PRODUCTS_CHANGE_SORTING = "products.change_sorting"

    # --- Категории ----------------------------------------------------------
    CATEGORIES_VIEW = "categories.view"
    CATEGORIES_CREATE = "categories.create"
    CATEGORIES_EDIT = "categories.edit"
    CATEGORIES_DELETE = "categories.delete"
    CATEGORIES_REORDER = "categories.reorder"
    CATEGORIES_ENABLE = "categories.enable"
    CATEGORIES_DISABLE = "categories.disable"

    # --- Позиции ------------------------------------------------------------
    POSITIONS_VIEW = "positions.view"
    POSITIONS_CREATE = "positions.create"
    POSITIONS_EDIT = "positions.edit"
    POSITIONS_DELETE = "positions.delete"
    POSITIONS_CHANGE_STATUS = "positions.change_status"
    POSITIONS_ARCHIVE = "positions.archive"

    # --- Местность: районы --------------------------------------------------
    DISTRICTS_VIEW = "districts.view"
    DISTRICTS_CREATE = "districts.create"
    DISTRICTS_EDIT = "districts.edit"
    DISTRICTS_DELETE = "districts.delete"

    # --- Местность: кастомные локации ---------------------------------------
    LOCATIONS_VIEW = "locations.view"
    LOCATIONS_CREATE = "locations.create"
    LOCATIONS_EDIT = "locations.edit"
    LOCATIONS_DELETE = "locations.delete"

    # --- Сотрудники ---------------------------------------------------------
    STAFF_VIEW = "staff.view"
    STAFF_INVITE = "staff.invite"
    STAFF_DISMISS = "staff.dismiss"
    STAFF_BLOCK = "staff.block"
    STAFF_UNBLOCK = "staff.unblock"
    STAFF_CHANGE_POSITION = "staff.change_position"
    STAFF_VIEW_STATS = "staff.view_stats"
    STAFF_VIEW_ACTIVITY = "staff.view_activity"

    # --- Должности (роли) ---------------------------------------------------
    ROLES_VIEW = "roles.view"
    ROLES_CREATE = "roles.create"
    ROLES_EDIT = "roles.edit"
    ROLES_DELETE = "roles.delete"
    ROLES_ASSIGN = "roles.assign"
    ROLES_ASSIGN_PERMISSIONS = "roles.assign_permissions"
    ROLES_COPY_PERMISSIONS = "roles.copy_permissions"
    ROLES_IMPORT_PERMISSIONS = "roles.import_permissions"
    ROLES_EXPORT_PERMISSIONS = "roles.export_permissions"

    # --- Бухгалтерия --------------------------------------------------------
    ACCOUNTING_VIEW = "accounting.view"
    ACCOUNTING_EXPORT = "accounting.export"

    # --- Реквизиты ----------------------------------------------------------
    REQUISITES_VIEW = "requisites.view"
    REQUISITES_CREATE = "requisites.create"
    REQUISITES_EDIT = "requisites.edit"
    REQUISITES_DELETE = "requisites.delete"
    REQUISITES_ENABLE = "requisites.enable"
    REQUISITES_DISABLE = "requisites.disable"
    REQUISITES_REORDER = "requisites.reorder"

    # --- Заявки на пополнение -----------------------------------------------
    TOPUPS_VIEW = "topups.view"
    TOPUPS_VIEW_ONE = "topups.view_one"
    TOPUPS_APPROVE = "topups.approve"
    TOPUPS_REJECT = "topups.reject"
    TOPUPS_COMMENT = "topups.comment"

    # --- Диспуты ------------------------------------------------------------
    DISPUTES_VIEW = "disputes.view"
    DISPUTES_VIEW_ONE = "disputes.view_one"
    DISPUTES_REPLY = "disputes.reply"
    DISPUTES_ATTACH_FILES = "disputes.attach_files"
    DISPUTES_CHANGE_STATUS = "disputes.change_status"
    DISPUTES_ASSIGN_RESPONSIBLE = "disputes.assign_responsible"
    DISPUTES_CLOSE = "disputes.close"
    DISPUTES_REOPEN = "disputes.reopen"
    DISPUTES_REFUND = "disputes.refund"
    DISPUTES_TRANSFER = "disputes.transfer"
    DISPUTES_MANAGE = "disputes.manage"

    # --- Отзывы -------------------------------------------------------------
    REVIEWS_VIEW = "reviews.view"
    REVIEWS_REPLY = "reviews.reply"
    REVIEWS_HIDE = "reviews.hide"
    REVIEWS_DELETE = "reviews.delete"
    REVIEWS_MODERATE = "reviews.moderate"

    # --- Настройки ----------------------------------------------------------
    SETTINGS_VIEW = "settings.view"
    SETTINGS_EDIT = "settings.edit"

    # --- Логи ---------------------------------------------------------------
    LOGS_VIEW = "logs.view"
    LOGS_DELETE = "logs.delete"

    # --- Система ------------------------------------------------------------
    STATS_VIEW = "stats.view"
    BACKUP_CREATE = "backup.create"
    BACKUP_RESTORE = "backup.restore"


@dataclass(frozen=True, slots=True)
class PermissionMeta:
    """Человекочитаемые метаданные одного права."""

    permission: Permission
    title: str
    group: PermissionGroup


def _meta(permission: Permission, title: str, group: PermissionGroup) -> PermissionMeta:
    return PermissionMeta(permission=permission, title=title, group=group)


# Метаданные всех прав (для админ-панели, экспорта/импорта, сидинга описаний).
PERMISSION_METADATA: dict[Permission, PermissionMeta] = {
    m.permission: m
    for m in (
        _meta(Permission.ADMIN_ACCESS, "Доступ в админ-панель", PermissionGroup.ADMIN),
        # Пользователи
        _meta(Permission.USERS_VIEW, "Просмотр пользователей", PermissionGroup.USERS),
        _meta(Permission.USERS_VIEW_ONE, "Просмотр пользователя", PermissionGroup.USERS),
        _meta(Permission.USERS_EDIT, "Изменение пользователя", PermissionGroup.USERS),
        _meta(Permission.USERS_EDIT_BALANCE, "Изменение баланса", PermissionGroup.USERS),
        _meta(Permission.USERS_BLOCK, "Блокировка пользователя", PermissionGroup.USERS),
        _meta(Permission.USERS_UNBLOCK, "Разблокировка пользователя", PermissionGroup.USERS),
        _meta(Permission.USERS_VIEW_ORDERS, "Просмотр заказов пользователя", PermissionGroup.USERS),
        _meta(
            Permission.USERS_VIEW_TRANSACTIONS,
            "Просмотр операций пользователя",
            PermissionGroup.USERS,
        ),
        _meta(
            Permission.USERS_VIEW_REVIEWS, "Просмотр отзывов пользователя", PermissionGroup.USERS
        ),
        _meta(
            Permission.USERS_VIEW_DISPUTES, "Просмотр диспутов пользователя", PermissionGroup.USERS
        ),
        # Заказы
        _meta(Permission.ORDERS_VIEW, "Просмотр заказов", PermissionGroup.ORDERS),
        _meta(Permission.ORDERS_VIEW_ONE, "Просмотр заказа", PermissionGroup.ORDERS),
        _meta(Permission.ORDERS_EDIT, "Изменение заказа", PermissionGroup.ORDERS),
        _meta(Permission.ORDERS_DELETE, "Удаление заказа", PermissionGroup.ORDERS),
        _meta(Permission.ORDERS_CHANGE_STATUS, "Изменение статуса заказа", PermissionGroup.ORDERS),
        _meta(Permission.ORDERS_REFUND, "Возврат по заказу", PermissionGroup.ORDERS),
        # Товары
        _meta(Permission.PRODUCTS_VIEW, "Просмотр товаров", PermissionGroup.PRODUCTS),
        _meta(Permission.PRODUCTS_CREATE, "Создание товара", PermissionGroup.PRODUCTS),
        _meta(Permission.PRODUCTS_EDIT, "Редактирование товара", PermissionGroup.PRODUCTS),
        _meta(Permission.PRODUCTS_DELETE, "Удаление товара", PermissionGroup.PRODUCTS),
        _meta(Permission.PRODUCTS_ARCHIVE, "Архивирование товара", PermissionGroup.PRODUCTS),
        _meta(Permission.PRODUCTS_HIDE, "Скрытие товара", PermissionGroup.PRODUCTS),
        _meta(Permission.PRODUCTS_CHANGE_PRICE, "Изменение цены товара", PermissionGroup.PRODUCTS),
        _meta(
            Permission.PRODUCTS_CHANGE_DESCRIPTION,
            "Изменение описания товара",
            PermissionGroup.PRODUCTS,
        ),
        _meta(Permission.PRODUCTS_CHANGE_PHOTOS, "Изменение фото товара", PermissionGroup.PRODUCTS),
        _meta(
            Permission.PRODUCTS_CHANGE_CATEGORY,
            "Изменение категории товара",
            PermissionGroup.PRODUCTS,
        ),
        _meta(
            Permission.PRODUCTS_CHANGE_SUBCATEGORY,
            "Изменение подкатегории товара",
            PermissionGroup.PRODUCTS,
        ),
        _meta(
            Permission.PRODUCTS_CHANGE_SORTING,
            "Изменение сортировки товара",
            PermissionGroup.PRODUCTS,
        ),
        # Категории
        _meta(Permission.CATEGORIES_VIEW, "Просмотр категорий", PermissionGroup.CATEGORIES),
        _meta(Permission.CATEGORIES_CREATE, "Создание категории", PermissionGroup.CATEGORIES),
        _meta(Permission.CATEGORIES_EDIT, "Редактирование категории", PermissionGroup.CATEGORIES),
        _meta(Permission.CATEGORIES_DELETE, "Удаление категории", PermissionGroup.CATEGORIES),
        _meta(
            Permission.CATEGORIES_REORDER, "Изменение порядка категорий", PermissionGroup.CATEGORIES
        ),
        _meta(Permission.CATEGORIES_ENABLE, "Включение категории", PermissionGroup.CATEGORIES),
        _meta(Permission.CATEGORIES_DISABLE, "Отключение категории", PermissionGroup.CATEGORIES),
        # Позиции
        _meta(Permission.POSITIONS_VIEW, "Просмотр позиций", PermissionGroup.POSITIONS),
        _meta(Permission.POSITIONS_CREATE, "Создание позиции", PermissionGroup.POSITIONS),
        _meta(Permission.POSITIONS_EDIT, "Редактирование позиции", PermissionGroup.POSITIONS),
        _meta(Permission.POSITIONS_DELETE, "Удаление позиции", PermissionGroup.POSITIONS),
        _meta(
            Permission.POSITIONS_CHANGE_STATUS,
            "Изменение статуса позиции",
            PermissionGroup.POSITIONS,
        ),
        _meta(Permission.POSITIONS_ARCHIVE, "Архивирование позиции", PermissionGroup.POSITIONS),
        # Местность
        _meta(Permission.DISTRICTS_VIEW, "Просмотр районов", PermissionGroup.LOCALITY),
        _meta(Permission.DISTRICTS_CREATE, "Создание района", PermissionGroup.LOCALITY),
        _meta(Permission.DISTRICTS_EDIT, "Редактирование района", PermissionGroup.LOCALITY),
        _meta(Permission.DISTRICTS_DELETE, "Удаление района", PermissionGroup.LOCALITY),
        _meta(Permission.LOCATIONS_VIEW, "Просмотр локаций", PermissionGroup.LOCALITY),
        _meta(Permission.LOCATIONS_CREATE, "Создание локации", PermissionGroup.LOCALITY),
        _meta(Permission.LOCATIONS_EDIT, "Редактирование локации", PermissionGroup.LOCALITY),
        _meta(Permission.LOCATIONS_DELETE, "Удаление локации", PermissionGroup.LOCALITY),
        # Сотрудники
        _meta(Permission.STAFF_VIEW, "Просмотр сотрудников", PermissionGroup.STAFF),
        _meta(Permission.STAFF_INVITE, "Приглашение сотрудника", PermissionGroup.STAFF),
        _meta(Permission.STAFF_DISMISS, "Увольнение сотрудника", PermissionGroup.STAFF),
        _meta(Permission.STAFF_BLOCK, "Блокировка сотрудника", PermissionGroup.STAFF),
        _meta(Permission.STAFF_UNBLOCK, "Разблокировка сотрудника", PermissionGroup.STAFF),
        _meta(
            Permission.STAFF_CHANGE_POSITION, "Смена должности сотрудника", PermissionGroup.STAFF
        ),
        _meta(Permission.STAFF_VIEW_STATS, "Просмотр статистики сотрудника", PermissionGroup.STAFF),
        _meta(
            Permission.STAFF_VIEW_ACTIVITY, "Просмотр активности сотрудника", PermissionGroup.STAFF
        ),
        # Должности
        _meta(Permission.ROLES_VIEW, "Просмотр должностей", PermissionGroup.ROLES),
        _meta(Permission.ROLES_CREATE, "Создание должности", PermissionGroup.ROLES),
        _meta(Permission.ROLES_EDIT, "Изменение должности", PermissionGroup.ROLES),
        _meta(Permission.ROLES_DELETE, "Удаление должности", PermissionGroup.ROLES),
        _meta(Permission.ROLES_ASSIGN, "Выдача должности", PermissionGroup.ROLES),
        _meta(
            Permission.ROLES_ASSIGN_PERMISSIONS, "Назначение прав должности", PermissionGroup.ROLES
        ),
        _meta(
            Permission.ROLES_COPY_PERMISSIONS,
            "Копирование прав между должностями",
            PermissionGroup.ROLES,
        ),
        _meta(Permission.ROLES_IMPORT_PERMISSIONS, "Импорт прав", PermissionGroup.ROLES),
        _meta(Permission.ROLES_EXPORT_PERMISSIONS, "Экспорт прав", PermissionGroup.ROLES),
        # Бухгалтерия
        _meta(Permission.ACCOUNTING_VIEW, "Просмотр бухгалтерии", PermissionGroup.ACCOUNTING),
        _meta(Permission.ACCOUNTING_EXPORT, "Экспорт отчётов", PermissionGroup.ACCOUNTING),
        # Реквизиты
        _meta(Permission.REQUISITES_VIEW, "Просмотр реквизитов", PermissionGroup.REQUISITES),
        _meta(Permission.REQUISITES_CREATE, "Создание реквизита", PermissionGroup.REQUISITES),
        _meta(Permission.REQUISITES_EDIT, "Изменение реквизита", PermissionGroup.REQUISITES),
        _meta(Permission.REQUISITES_DELETE, "Удаление реквизита", PermissionGroup.REQUISITES),
        _meta(Permission.REQUISITES_ENABLE, "Включение реквизита", PermissionGroup.REQUISITES),
        _meta(Permission.REQUISITES_DISABLE, "Отключение реквизита", PermissionGroup.REQUISITES),
        _meta(Permission.REQUISITES_REORDER, "Приоритет реквизитов", PermissionGroup.REQUISITES),
        # Заявки на пополнение
        _meta(Permission.TOPUPS_VIEW, "Просмотр заявок", PermissionGroup.TOPUPS),
        _meta(Permission.TOPUPS_VIEW_ONE, "Просмотр заявки", PermissionGroup.TOPUPS),
        _meta(Permission.TOPUPS_APPROVE, "Подтверждение заявки", PermissionGroup.TOPUPS),
        _meta(Permission.TOPUPS_REJECT, "Отклонение заявки", PermissionGroup.TOPUPS),
        _meta(Permission.TOPUPS_COMMENT, "Комментарий к заявке", PermissionGroup.TOPUPS),
        # Диспуты
        _meta(Permission.DISPUTES_VIEW, "Просмотр диспутов", PermissionGroup.DISPUTES),
        _meta(Permission.DISPUTES_VIEW_ONE, "Просмотр диспута", PermissionGroup.DISPUTES),
        _meta(Permission.DISPUTES_REPLY, "Ответ в диспуте", PermissionGroup.DISPUTES),
        _meta(
            Permission.DISPUTES_ATTACH_FILES,
            "Прикрепление файлов в диспуте",
            PermissionGroup.DISPUTES,
        ),
        _meta(
            Permission.DISPUTES_CHANGE_STATUS, "Изменение статуса диспута", PermissionGroup.DISPUTES
        ),
        _meta(
            Permission.DISPUTES_ASSIGN_RESPONSIBLE,
            "Изменение ответственного диспута",
            PermissionGroup.DISPUTES,
        ),
        _meta(Permission.DISPUTES_CLOSE, "Закрытие диспута", PermissionGroup.DISPUTES),
        _meta(Permission.DISPUTES_REOPEN, "Повторное открытие диспута", PermissionGroup.DISPUTES),
        _meta(
            Permission.DISPUTES_REFUND, "Оформление возврата в диспуте", PermissionGroup.DISPUTES
        ),
        _meta(
            Permission.DISPUTES_TRANSFER, "Передача диспута сотруднику", PermissionGroup.DISPUTES
        ),
        _meta(Permission.DISPUTES_MANAGE, "Управление диспутами", PermissionGroup.DISPUTES),
        # Отзывы
        _meta(Permission.REVIEWS_VIEW, "Просмотр отзывов", PermissionGroup.REVIEWS),
        _meta(Permission.REVIEWS_REPLY, "Ответ на отзыв", PermissionGroup.REVIEWS),
        _meta(Permission.REVIEWS_HIDE, "Скрытие отзыва", PermissionGroup.REVIEWS),
        _meta(Permission.REVIEWS_DELETE, "Удаление отзыва", PermissionGroup.REVIEWS),
        _meta(Permission.REVIEWS_MODERATE, "Модерация отзывов", PermissionGroup.REVIEWS),
        # Настройки
        _meta(Permission.SETTINGS_VIEW, "Просмотр настроек", PermissionGroup.SETTINGS),
        _meta(Permission.SETTINGS_EDIT, "Изменение настроек", PermissionGroup.SETTINGS),
        # Логи
        _meta(Permission.LOGS_VIEW, "Просмотр логов", PermissionGroup.LOGS),
        _meta(Permission.LOGS_DELETE, "Удаление логов", PermissionGroup.LOGS),
        # Система
        _meta(Permission.STATS_VIEW, "Просмотр статистики", PermissionGroup.SYSTEM),
        _meta(Permission.BACKUP_CREATE, "Резервное копирование", PermissionGroup.SYSTEM),
        _meta(Permission.BACKUP_RESTORE, "Восстановление базы", PermissionGroup.SYSTEM),
    )
}

# Полный список прав (для сидинга).
ALL_PERMISSIONS: tuple[Permission, ...] = tuple(Permission)

# Права, дающие сотруднику автоматическое участие в диспуте (см. ТЗ).
DISPUTE_PARTICIPANT_PERMISSIONS: tuple[Permission, ...] = (
    Permission.DISPUTES_VIEW,
    Permission.DISPUTES_REPLY,
    Permission.DISPUTES_CLOSE,
    Permission.DISPUTES_MANAGE,
)


def grouped_permissions() -> dict[PermissionGroup, list[PermissionMeta]]:
    """Сгруппировать метаданные прав по группам (для админ-панели)."""
    result: dict[PermissionGroup, list[PermissionMeta]] = defaultdict(list)
    for meta in PERMISSION_METADATA.values():
        result[meta.group].append(meta)
    return dict(result)


# Гарантируем на этапе импорта, что метаданные описаны для КАЖДОГО права.
_missing = set(Permission) - set(PERMISSION_METADATA)
if _missing:  # pragma: no cover - защита целостности реестра
    raise RuntimeError(f"Нет метаданных для прав: {sorted(p.value for p in _missing)}")
