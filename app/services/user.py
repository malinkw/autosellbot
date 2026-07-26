"""Служба пользователей: онбординг, профиль, блокировки, поиск."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models import Order, Review, User
from app.models.enums import AccountStatus
from app.repositories.user import UserRepository
from app.utils.ids import generate_public_id
from app.utils.pagination import Page, Paginator

NICKNAME_MIN = 3
NICKNAME_MAX = 20


@dataclass(slots=True)
class ProfileStats:
    """Агрегированные показатели профиля пользователя."""

    orders_count: int
    reviews_count: int


class UserService:
    """Бизнес-логика работы с пользователями."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserRepository(session)

    async def get_or_create(
        self,
        telegram_id: int,
        *,
        username: str | None = None,
        full_name: str | None = None,
    ) -> tuple[User, bool]:
        """Найти пользователя по Telegram ID или создать нового.

        Возвращает кортеж ``(user, created)``.
        """
        user = await self._repo.get_by_telegram_id(telegram_id)
        if user is not None:
            changed = False
            if username is not None and user.username != username:
                user.username = username
                changed = True
            if full_name is not None and user.full_name != full_name:
                user.full_name = full_name
                changed = True
            user.last_activity_at = datetime.now(UTC)
            if changed:
                await self._session.flush()
            return user, False

        user = await self._repo.create(
            telegram_id=telegram_id,
            public_id=await self._unique_public_id(),
            username=username,
            full_name=full_name,
            last_activity_at=datetime.now(UTC),
        )
        return user, True

    async def _unique_public_id(self) -> str:
        for _ in range(20):
            candidate = generate_public_id()
            if not await self._repo.public_id_exists(candidate):
                return candidate
        raise ConflictError("Не удалось сгенерировать уникальный публичный ID")

    @staticmethod
    def validate_nickname(nickname: str) -> str:
        """Проверить формат ника и вернуть нормализованное значение."""
        value = nickname.strip()
        if not (NICKNAME_MIN <= len(value) <= NICKNAME_MAX):
            raise ValidationError(
                f"Ник должен содержать от {NICKNAME_MIN} до {NICKNAME_MAX} символов."
            )
        if not all(ch.isalnum() or ch in "_-" for ch in value):
            raise ValidationError("Ник может содержать буквы, цифры, «_» и «-».")
        return value

    async def set_nickname(self, user: User, nickname: str) -> User:
        """Назначить уникальный ник пользователю (завершает онбординг)."""
        value = self.validate_nickname(nickname)
        if await self._repo.nickname_taken(value):
            raise ConflictError("Этот ник уже занят, выберите другой.")
        user.nickname = value
        user.onboarded = True
        await self._session.flush()
        return user

    async def get(self, user_id: uuid.UUID) -> User:
        """Получить пользователя по ID или выбросить :class:`NotFoundError`."""
        user = await self._repo.get(user_id)
        if user is None:
            raise NotFoundError("Пользователь не найден.")
        return user

    async def profile_stats(self, user_id: uuid.UUID) -> ProfileStats:
        """Посчитать количество заказов и отзывов пользователя."""
        orders = int(
            (
                await self._session.execute(
                    select(func.count(Order.id)).where(Order.user_id == user_id)
                )
            ).scalar_one()
        )
        reviews = int(
            (
                await self._session.execute(
                    select(func.count(Review.id)).where(
                        Review.user_id == user_id, Review.deleted_at.is_(None)
                    )
                )
            ).scalar_one()
        )
        return ProfileStats(orders_count=orders, reviews_count=reviews)

    async def block(self, user: User) -> User:
        """Заблокировать пользователя."""
        user.status = AccountStatus.BLOCKED
        await self._session.flush()
        return user

    async def unblock(self, user: User) -> User:
        """Разблокировать пользователя."""
        user.status = AccountStatus.ACTIVE
        await self._session.flush()
        return user

    async def search(self, query: str) -> list[User]:
        """Поиск пользователей по ID/нику/username."""
        return await self._repo.search(query)

    async def staff_with_permission(self, permission_code: str) -> list[User]:
        """Активные сотрудники, чья должность имеет указанное право."""
        return await self._repo.staff_with_permission(permission_code)

    async def paginate(self, paginator: Paginator) -> Page[User]:
        """Постраничный список пользователей."""
        return await self._repo.paginate(paginator, order_by=[User.created_at.desc()])
