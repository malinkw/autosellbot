"""Фабрики callback-данных (aiogram :class:`CallbackData`)."""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class MenuCB(CallbackData, prefix="menu"):
    """Навигация по главному меню."""

    action: str


class CatalogCB(CallbackData, prefix="cat"):
    """Навигация по каталогу.

    ``action``: ``root`` | ``open`` (категория) | ``product`` | ``buy``.
    """

    action: str
    id: str = ""


class OrderCB(CallbackData, prefix="ord"):
    """Заказы пользователя. ``action``: ``list`` | ``view``."""

    action: str
    id: str = ""


class WalletCB(CallbackData, prefix="wal"):
    """Кошелёк. ``action``: ``open`` | ``history`` | ``topup`` | ``requisites``."""

    action: str
    id: str = ""


class DisputeCB(CallbackData, prefix="dsp"):
    """Диспуты. ``action``: ``open`` | ``list`` | ``view`` | ``reply`` | ``history``."""

    action: str
    id: str = ""


class ReviewCB(CallbackData, prefix="rev"):
    """Отзывы. ``action``: ``leave`` | ``rate``."""

    action: str
    id: str = ""
    value: int = 0


class AdminCB(CallbackData, prefix="adm"):
    """Действия административной панели.

    :param section: раздел (``users``, ``roles``, ``topups`` и т.д.).
    :param action: действие внутри раздела.
    :param id: идентификатор целевой сущности (если применимо).
    :param arg: дополнительный аргумент (код права, статус, формат экспорта).
    """

    section: str
    action: str = "open"
    id: str = ""
    arg: str = ""


class PageCB(CallbackData, prefix="pg"):
    """Пагинация списков."""

    scope: str
    page: int = 1
    ref: str = ""


class ConfirmCB(CallbackData, prefix="cfm"):
    """Подтверждение действия."""

    action: str
    id: str = ""
    yes: bool = True
