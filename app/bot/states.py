"""Группы состояний FSM для многошаговых сценариев."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Onboarding(StatesGroup):
    """Первичная регистрация: выбор ника."""

    choosing_nickname = State()


class CatalogSearch(StatesGroup):
    """Поиск товара."""

    query = State()


class TopUp(StatesGroup):
    """Заявка на пополнение: сумма и PDF-чек."""

    amount = State()
    receipt = State()


class DisputeOpen(StatesGroup):
    """Открытие диспута."""

    subject = State()


class DisputeReply(StatesGroup):
    """Ответ в диспуте (пользователь)."""

    message = State()


class DisputeReplyAdmin(StatesGroup):
    """Ответ в диспуте (сотрудник из админ-панели)."""

    message = State()


class ReviewFlow(StatesGroup):
    """Оставление отзыва: текст после выбора оценки."""

    text = State()


# --- Административные сценарии ------------------------------------------------
class CategoryForm(StatesGroup):
    """Создание категории."""

    name = State()


class ProductForm(StatesGroup):
    """Создание товара."""

    name = State()
    price = State()
    description = State()


class PositionForm(StatesGroup):
    """Создание позиции."""

    content = State()


class DistrictForm(StatesGroup):
    """Создание района."""

    name = State()


class LocationForm(StatesGroup):
    """Создание локации."""

    name = State()


class RoleForm(StatesGroup):
    """Создание должности."""

    name = State()


class StaffForm(StatesGroup):
    """Приглашение сотрудника."""

    username = State()
    role = State()


class RequisiteForm(StatesGroup):
    """Создание реквизита."""

    value = State()
    holder = State()


class BalanceForm(StatesGroup):
    """Ручная корректировка баланса пользователя."""

    amount = State()
    comment = State()


class SettingForm(StatesGroup):
    """Изменение текстовой настройки."""

    value = State()


class ReviewReplyForm(StatesGroup):
    """Ответ администрации на отзыв."""

    text = State()


class SearchForm(StatesGroup):
    """Универсальный административный поиск."""

    query = State()
