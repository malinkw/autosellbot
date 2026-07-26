"""Генерация человекочитаемых публичных идентификаторов и номеров."""

from __future__ import annotations

import secrets
import string
from datetime import UTC, datetime

_ALPHABET = string.ascii_uppercase + string.digits


def generate_public_id(length: int = 8) -> str:
    """Сгенерировать короткий публичный ID пользователя (например, ``7F3KQ9AZ``)."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def generate_number(prefix: str) -> str:
    """Сгенерировать номер сущности вида ``ORD-240726-AB12``.

    :param prefix: префикс типа (``ORD``, ``DSP``, ``TOP``).
    """
    stamp = datetime.now(UTC).strftime("%y%m%d")
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(4))
    return f"{prefix}-{stamp}-{suffix}"
