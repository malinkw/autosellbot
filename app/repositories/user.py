"""Репозиторий пользователей и сотрудников."""

from __future__ import annotations

from sqlalchemy import or_, select

from app.models import Role, RolePermission, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Доступ к данным пользователей."""

    model = User

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Найти пользователя по Telegram ID."""
        return await self.get_by(telegram_id=telegram_id)

    async def get_by_public_id(self, public_id: str) -> User | None:
        """Найти пользователя по публичному ID."""
        return await self.get_by(public_id=public_id)

    async def get_by_nickname(self, nickname: str) -> User | None:
        """Найти пользователя по нику."""
        return await self.get_by(nickname=nickname)

    async def get_by_username(self, username: str) -> User | None:
        """Найти пользователя по Telegram username (без ведущего @)."""
        return await self.get_by(username=username.lstrip("@"))

    async def nickname_taken(self, nickname: str) -> bool:
        """Проверить занятость ника (регистронезависимо)."""
        stmt = self._base_select().where(User.nickname.ilike(nickname))
        return (await self.session.execute(stmt)).scalars().first() is not None

    async def public_id_exists(self, public_id: str) -> bool:
        """Проверить существование публичного ID."""
        return await self.exists(public_id=public_id)

    async def search(self, query: str, *, limit: int = 20) -> list[User]:
        """Поиск по публичному ID, нику или username."""
        like = f"%{query.strip().lstrip('@')}%"
        stmt = (
            self._base_select()
            .where(
                or_(
                    User.public_id.ilike(like),
                    User.nickname.ilike(like),
                    User.username.ilike(like),
                )
            )
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def staff_with_permission(self, permission_code: str) -> list[User]:
        """Все активные сотрудники, чья должность имеет указанное право."""
        stmt = (
            select(User)
            .join(Role, User.role_id == Role.id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .where(
                User.deleted_at.is_(None),
                User.is_staff.is_(True),
                RolePermission.permission_code == permission_code,
            )
        )
        return list((await self.session.execute(stmt)).scalars().unique().all())

    async def list_staff(self) -> list[User]:
        """Список всех сотрудников."""
        return await self.list(filters=[User.is_staff.is_(True)], order_by=[User.created_at.desc()])
