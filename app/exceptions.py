"""Доменные исключения приложения (централизованная обработка ошибок)."""

from __future__ import annotations


class AppError(Exception):
    """Базовое доменное исключение с человекочитаемым сообщением."""

    message: str = "Произошла ошибка."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.message = message or self.message


class NotFoundError(AppError):
    """Запрашиваемая сущность не найдена."""

    message = "Запись не найдена."


class PermissionDeniedError(AppError):
    """У пользователя нет требуемого права."""

    message = "Недостаточно прав для выполнения действия."

    def __init__(self, permission: str | None = None) -> None:
        msg = "Недостаточно прав для выполнения действия."
        if permission:
            msg = f"Недостаточно прав: {permission}"
        super().__init__(msg)
        self.permission = permission


class ValidationError(AppError):
    """Некорректные входные данные."""

    message = "Некорректные данные."


class ConflictError(AppError):
    """Нарушение уникальности/конфликт состояния."""

    message = "Конфликт данных."


class BusinessRuleError(AppError):
    """Нарушено бизнес-правило (например, окно диспута истекло)."""

    message = "Действие невозможно по правилам системы."


class InsufficientFundsError(BusinessRuleError):
    """Недостаточно средств на балансе."""

    message = "Недостаточно средств на балансе."
