"""Общие помощники админ-хендлеров."""

from __future__ import annotations

from aiogram.types import CallbackQuery


async def edit(callback: CallbackQuery, text: str, markup=None) -> None:  # type: ignore[no-untyped-def]
    """Безопасно отредактировать сообщение (или ответить, если редактирование невозможно)."""
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except Exception:
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer()
