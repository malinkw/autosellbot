"""Тесты целостности реестра прав."""

from __future__ import annotations

from app.permissions import ALL_PERMISSIONS, PERMISSION_METADATA, Permission
from app.permissions.registry import DISPUTE_PARTICIPANT_PERMISSIONS


def test_every_permission_has_metadata() -> None:
    """У каждого права есть метаданные (title/group)."""
    for permission in Permission:
        assert permission in PERMISSION_METADATA
        assert PERMISSION_METADATA[permission].title


def test_permission_codes_unique() -> None:
    """Коды прав уникальны."""
    codes = [p.value for p in ALL_PERMISSIONS]
    assert len(codes) == len(set(codes))


def test_dispute_participant_permissions_are_valid() -> None:
    """Права авто-участия в диспуте входят в общий реестр."""
    for permission in DISPUTE_PARTICIPANT_PERMISSIONS:
        assert permission in set(Permission)


def test_registry_is_substantial() -> None:
    """Реестр покрывает десятки атомарных прав (гранулярность RBAC)."""
    assert len(ALL_PERMISSIONS) >= 70
