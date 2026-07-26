"""Фабрики бота и диспетчера aiogram с подключением middlewares и роутеров."""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.config import Settings
from app.database import Database
from app.middlewares import (
    AuthMiddleware,
    DatabaseMiddleware,
    LoggingMiddleware,
    ThrottlingMiddleware,
)


def build_bot(settings: Settings) -> Bot:
    """Создать экземпляр :class:`aiogram.Bot`."""
    return Bot(
        token=settings.bot.token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def build_dispatcher(
    *, settings: Settings, database: Database, redis: Redis, bot: Bot
) -> Dispatcher:
    """Создать и настроить :class:`aiogram.Dispatcher`.

    Регистрирует внешние middlewares (логирование → троттлинг → сессия → авторизация)
    и подключает все роутеры.
    """
    storage = RedisStorage(redis)
    dispatcher = Dispatcher(storage=storage)

    dispatcher.update.outer_middleware(LoggingMiddleware())
    dispatcher.update.outer_middleware(
        ThrottlingMiddleware(redis, rate=settings.app.rate_limit_per_second)
    )
    dispatcher.update.outer_middleware(DatabaseMiddleware(database, settings, redis, bot))
    dispatcher.update.outer_middleware(AuthMiddleware())

    from app.handlers import get_routers

    for router in get_routers():
        dispatcher.include_router(router)

    return dispatcher
