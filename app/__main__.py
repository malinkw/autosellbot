"""Точка входа приложения: инициализация и запуск бота (long polling)."""

from __future__ import annotations

import asyncio
import contextlib

from app.bot import build_bot, build_dispatcher
from app.config import get_settings
from app.database import get_database
from app.database.redis import RedisProvider
from app.database.seed import seed_all
from app.logging import get_logger, setup_logging
from app.scheduler import build_scheduler


async def main() -> None:
    """Собрать зависимости, запустить планировщик и polling."""
    settings = get_settings()
    setup_logging(
        log_dir=settings.app.log_dir,
        level=settings.app.log_level,
        development=settings.app.is_development,
    )
    log = get_logger("bot")
    log.info("startup", env=str(settings.app.env))

    database = get_database(settings)
    redis_provider = RedisProvider(settings)
    redis = redis_provider.client

    # Идемпотентный сидинг справочных данных.
    async with database.session() as session:
        await seed_all(session)

    bot = build_bot(settings)
    dispatcher = build_dispatcher(settings=settings, database=database, redis=redis, bot=bot)

    scheduler = build_scheduler(settings)
    scheduler.start()

    try:
        if settings.bot.drop_pending_updates:
            await bot.delete_webhook(drop_pending_updates=True)
        me = await bot.get_me()
        log.info("bot_started", username=me.username)
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        log.info("shutdown")
        scheduler.shutdown(wait=False)
        await bot.session.close()
        await redis_provider.close()
        await database.dispose()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt, SystemExit):
        asyncio.run(main())
