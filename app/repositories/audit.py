"""Репозиторий журнала аудита."""

from __future__ import annotations

from app.models import AuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    """Доступ к журналу аудита."""

    model = AuditLog

    async def recent(self, *, limit: int = 50) -> list[AuditLog]:
        """Последние записи аудита."""
        return await self.list(order_by=[AuditLog.created_at.desc()], limit=limit)
