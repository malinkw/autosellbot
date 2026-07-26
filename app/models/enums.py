"""Перечисления доменных статусов и типов."""

from __future__ import annotations

from enum import StrEnum


class AccountStatus(StrEnum):
    """Статус аккаунта пользователя/сотрудника."""

    ACTIVE = "active"
    BLOCKED = "blocked"


class OrderStatus(StrEnum):
    """Статусы заказа (жизненный цикл из ТЗ)."""

    CREATED = "created"  # Создан
    AWAITING_CONFIRMATION = "awaiting_confirmation"  # Ожидает подтверждения
    PROCESSING = "processing"  # В обработке
    READY = "ready"  # Готов
    COMPLETED = "completed"  # Завершён
    CANCELLED = "cancelled"  # Отменён
    REFUNDED = "refunded"  # Возврат


ORDER_STATUS_TITLES: dict[OrderStatus, str] = {
    OrderStatus.CREATED: "Создан",
    OrderStatus.AWAITING_CONFIRMATION: "Ожидает подтверждения",
    OrderStatus.PROCESSING: "В обработке",
    OrderStatus.READY: "Готов",
    OrderStatus.COMPLETED: "Завершён",
    OrderStatus.CANCELLED: "Отменён",
    OrderStatus.REFUNDED: "Возврат",
}


class PositionStatus(StrEnum):
    """Статус позиции выдачи."""

    AVAILABLE = "available"  # Доступна
    RESERVED = "reserved"  # Зарезервирована под заказ
    SOLD = "sold"  # Продана
    ARCHIVED = "archived"  # В архиве


POSITION_STATUS_TITLES: dict[PositionStatus, str] = {
    PositionStatus.AVAILABLE: "Доступна",
    PositionStatus.RESERVED: "Зарезервирована",
    PositionStatus.SOLD: "Продана",
    PositionStatus.ARCHIVED: "В архиве",
}


class DisputeStatus(StrEnum):
    """Статусы диспута."""

    OPEN = "open"  # Открыт
    IN_REVIEW = "in_review"  # На рассмотрении
    RESOLVED = "resolved"  # Решён
    CLOSED = "closed"  # Закрыт
    REFUNDED = "refunded"  # Возврат оформлен


DISPUTE_STATUS_TITLES: dict[DisputeStatus, str] = {
    DisputeStatus.OPEN: "Открыт",
    DisputeStatus.IN_REVIEW: "На рассмотрении",
    DisputeStatus.RESOLVED: "Решён",
    DisputeStatus.CLOSED: "Закрыт",
    DisputeStatus.REFUNDED: "Возврат оформлен",
}


class DisputeActionType(StrEnum):
    """Типы действий в неизменяемой истории диспута."""

    CREATED = "created"
    PARTICIPANT_ADDED = "participant_added"
    RESPONSIBLE_ASSIGNED = "responsible_assigned"
    RESPONSIBLE_CHANGED = "responsible_changed"
    MESSAGE = "message"
    STATUS_CHANGED = "status_changed"
    REFUNDED = "refunded"
    TRANSFERRED = "transferred"
    REOPENED = "reopened"
    CLOSED = "closed"


class TransactionType(StrEnum):
    """Типы операций по кошельку."""

    TOPUP = "topup"  # Пополнение
    PURCHASE = "purchase"  # Списание за заказ
    REFUND = "refund"  # Возврат
    ACCRUAL = "accrual"  # Начисление
    MANUAL = "manual"  # Ручная корректировка


TRANSACTION_TYPE_TITLES: dict[TransactionType, str] = {
    TransactionType.TOPUP: "Пополнение",
    TransactionType.PURCHASE: "Списание",
    TransactionType.REFUND: "Возврат",
    TransactionType.ACCRUAL: "Начисление",
    TransactionType.MANUAL: "Ручная корректировка",
}


class TopUpStatus(StrEnum):
    """Статусы заявки на пополнение."""

    CREATED = "created"  # Создана
    CHECKING = "checking"  # Проверяется
    APPROVED = "approved"  # Подтверждена
    REJECTED = "rejected"  # Отклонена


TOPUP_STATUS_TITLES: dict[TopUpStatus, str] = {
    TopUpStatus.CREATED: "Создана",
    TopUpStatus.CHECKING: "Проверяется",
    TopUpStatus.APPROVED: "Подтверждена",
    TopUpStatus.REJECTED: "Отклонена",
}


class RequisiteType(StrEnum):
    """Тип платёжного реквизита."""

    CARD = "card"  # Банковская карта
    SBP = "sbp"  # Номер СБП


REQUISITE_TYPE_TITLES: dict[RequisiteType, str] = {
    RequisiteType.CARD: "Банковская карта",
    RequisiteType.SBP: "СБП",
}
