"""Общие фикстуры для тестов (in-memory SQLite)."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from decimal import Decimal

os.environ.setdefault("APP__ENV", "testing")
os.environ.setdefault("BOT__TOKEN", "123456:test-token")
os.environ.setdefault("BOT__ADMIN_IDS", "[999999]")

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.database.seed import seed_all
from app.models import Base, Category, Product, User
from app.models.enums import PositionStatus
from app.services.position import PositionService


@pytest.fixture(scope="session")
def settings() -> Settings:
    """Настройки приложения для тестов."""
    return get_settings()


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Свежая БД в памяти на каждый тест, со стартовым сидингом."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db_session:
        await seed_all(db_session)
        yield db_session
    await engine.dispose()


async def make_user(
    session: AsyncSession,
    *,
    telegram_id: int = 1,
    balance: Decimal = Decimal("0.00"),
    public_id: str | None = None,
) -> User:
    """Создать пользователя с заданным балансом."""
    user = User(
        telegram_id=telegram_id,
        public_id=public_id or f"U{telegram_id:07d}",
        nickname=f"user{telegram_id}",
        balance=balance,
        onboarded=True,
    )
    session.add(user)
    await session.flush()
    return user


async def make_product(session: AsyncSession, *, price: Decimal = Decimal("100.00")) -> Product:
    """Создать категорию и товар."""
    category = Category(name="Тест", sort_order=1)
    session.add(category)
    await session.flush()
    product = Product(name="Товар", price=price, category_id=category.id)
    session.add(product)
    await session.flush()
    return product


async def add_position(
    session: AsyncSession, product: Product, creator: User, *, content: str = "SECRET"
) -> None:
    """Добавить доступную позицию к товару."""
    service = PositionService(session)
    position = await service.create(product_id=product.id, content=content, creator=creator)
    assert position.status is PositionStatus.AVAILABLE
