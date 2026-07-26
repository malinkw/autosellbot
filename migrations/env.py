"""Окружение Alembic (асинхронный движок, метаданные из моделей приложения)."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from app.config import get_settings

# Импорт пакета моделей регистрирует все таблицы в Base.metadata.
from app.models import Base
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Подставляем DSN из настроек приложения.
_settings = get_settings()
config.set_main_option("sqlalchemy.url", _settings.db.dsn)


def run_migrations_offline() -> None:
    """Миграции в offline-режиме (генерация SQL без подключения)."""
    context.configure(
        url=_settings.db.dsn,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Миграции в online-режиме через async-движок."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _settings.db.dsn
    connectable = async_engine_from_config(configuration, prefix="sqlalchemy.", poolclass=NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
