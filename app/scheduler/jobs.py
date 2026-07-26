"""Реализация периодических задач планировщика."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.config import Settings
from app.database import get_database
from app.logging import get_logger
from app.models import Dispute
from app.models.dispute import DisputeHistory
from app.models.enums import DisputeActionType, DisputeStatus
from app.services.backup import BackupService

log = get_logger("bot")


async def scheduled_backup(settings: Settings) -> None:
    """Создать резервную копию БД по расписанию."""
    try:
        path = await BackupService(settings).create()
        log.info("scheduled_backup_done", path=str(path))
    except Exception as exc:
        log.error("scheduled_backup_failed", error=str(exc), channel="errors")


async def auto_close_dispute_windows(settings: Settings) -> None:
    """Автоматически закрыть диспуты, отмеченные «Решён» более 24 часов назад."""
    database = get_database(settings)
    threshold = datetime.now(UTC) - timedelta(hours=24)
    async with database.session() as session:
        stmt = select(Dispute).where(
            Dispute.status == DisputeStatus.RESOLVED,
            Dispute.updated_at < threshold,
            Dispute.deleted_at.is_(None),
        )
        disputes = list((await session.execute(stmt)).scalars().all())
        for dispute in disputes:
            dispute.status = DisputeStatus.CLOSED
            dispute.closed_at = datetime.now(UTC)
            session.add(
                DisputeHistory(
                    dispute_id=dispute.id,
                    actor_id=None,
                    action=DisputeActionType.CLOSED,
                    details="Автоматическое закрытие по истечении срока",
                )
            )
        if disputes:
            log.info("disputes_auto_closed", count=len(disputes))
