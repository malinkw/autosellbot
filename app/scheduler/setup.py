"""Настройка APScheduler и регистрация периодических задач."""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import Settings
from app.logging import get_logger
from app.scheduler.jobs import auto_close_dispute_windows, scheduled_backup

log = get_logger("bot")


def build_scheduler(settings: Settings) -> AsyncIOScheduler:
    """Создать планировщик и зарегистрировать задачи.

    Задачи:
    * ежедневный бэкап БД по cron из настроек;
    * периодическая проверка окон диспутов (перевод «Решён» → «Закрыт» по TTL).
    """
    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        scheduled_backup,
        CronTrigger.from_crontab(settings.app.backup_cron, timezone="UTC"),
        args=[settings],
        id="daily_backup",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        auto_close_dispute_windows,
        "interval",
        hours=1,
        args=[settings],
        id="dispute_window_check",
        replace_existing=True,
    )
    log.info("scheduler_configured", backup_cron=settings.app.backup_cron)
    return scheduler
