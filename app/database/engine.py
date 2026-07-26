"""Асинхронный движок SQLAlchemy и фабрика сессий."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import Settings


class Database:
    """Обёртка над async-движком и фабрикой сессий."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        if settings.app.is_testing:
            # SQLite/тесты: без размерного пула, чтобы не конфликтовать с драйвером.
            self._engine = create_async_engine(
                settings.db.dsn, echo=settings.db.echo, poolclass=NullPool
            )
        else:
            self._engine = create_async_engine(
                settings.db.dsn,
                echo=settings.db.echo,
                pool_pre_ping=True,
                pool_size=settings.db.pool_size,
                max_overflow=settings.db.max_overflow,
            )
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        """Экземпляр async-движка."""
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Фабрика сессий (для middleware и сервисов)."""
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Контекстный менеджер транзакционной сессии.

        Коммитит при успешном выходе, откатывает при исключении и всегда
        закрывает сессию.
        """
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def dispose(self) -> None:
        """Закрыть пул соединений."""
        await self._engine.dispose()


_database: Database | None = None


def get_database(settings: Settings) -> Database:
    """Вернуть синглтон :class:`Database`."""
    global _database
    if _database is None:
        _database = Database(settings)
    return _database
