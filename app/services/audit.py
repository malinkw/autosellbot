"""Служба аудита: единая точка записи значимых действий в журнал."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models import AuditLog, User
from app.repositories.audit import AuditRepository
from app.utils.pagination import Page, Paginator


class AuditService:
    """Запись и чтение журнала аудита."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AuditRepository(session)

    async def record(
        self,
        action: str,
        *,
        actor: User | None = None,
        channel: str = "bot",
        entity_type: str | None = None,
        entity_id: str | uuid.UUID | None = None,
        old_data: dict[str, Any] | None = None,
        new_data: dict[str, Any] | None = None,
        result: str = "success",
        ip: str | None = None,
        message: str | None = None,
    ) -> AuditLog:
        """Создать запись аудита и продублировать её в файловый журнал канала."""
        entry = await self._repo.create(
            action=action,
            channel=channel,
            actor_id=actor.id if actor else None,
            actor_telegram_id=actor.telegram_id if actor else None,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            old_data=old_data,
            new_data=new_data,
            result=result,
            ip=ip,
            message=message,
        )
        get_logger(channel).info(
            "audit",
            action=action,
            actor_id=str(actor.id) if actor else None,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            result=result,
        )
        return entry

    async def list_all(self, paginator: Paginator) -> Page[AuditLog]:
        """Постраничный просмотр журнала аудита."""
        return await self._repo.paginate(paginator, order_by=[AuditLog.created_at.desc()])

    async def purge(self) -> int:
        """Полностью очистить журнал аудита (право ``logs.delete``)."""
        entries = await self._repo.list()
        for entry in entries:
            await self._repo.hard_delete(entry)
        return len(entries)
