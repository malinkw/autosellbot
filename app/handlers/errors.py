"""Централизованная обработка ошибок хендлеров."""

from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery, ErrorEvent, Message

from app.exceptions import AppError
from app.logging import get_logger

router = Router(name="errors")
log = get_logger("errors")


@router.errors()
async def on_error(event: ErrorEvent) -> bool:
    """Единая точка обработки исключений.

    Доменные ошибки (:class:`AppError`) показываются пользователю понятным текстом;
    прочие — логируются, пользователю выдаётся общее сообщение.
    """
    exc = event.exception
    update = event.update

    message: Message | None = update.message
    callback: CallbackQuery | None = update.callback_query

    if isinstance(exc, AppError):
        text = f"⚠️ {exc.message}"
        if callback is not None:
            await callback.answer(exc.message, show_alert=True)
        elif message is not None:
            await message.answer(text)
        return True

    log.exception("unhandled_error", error=str(exc), channel="errors")
    text = "❌ Произошла внутренняя ошибка. Попробуйте позже."
    try:
        if callback is not None:
            await callback.answer(text, show_alert=True)
        elif message is not None:
            await message.answer(text)
    except Exception:
        pass
    return True
