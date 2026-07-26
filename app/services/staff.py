"""Служба сотрудников: приём, увольнение, блокировки, статистика."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ConflictError, NotFoundError
from app.models import Position, User
from app.models.enums import AccountStatus
from app.repositories.rbac import RoleRepository
from app.repositories.user import UserRepository
from app.utils.formatting import dt


@dataclass(slots=True)
class StaffStats:
    """Статистика сотрудника."""

    positions_created: int
    last_activity: str


class StaffService:
    """Управление сотрудниками."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._roles = RoleRepository(session)

    async def list_all(self) -> list[User]:
        """Список сотрудников."""
        return await self._users.list_staff()

    async def invite(self, username: str, role_id: uuid.UUID) -> User:
        """Назначить существующего пользователя сотрудником с должностью.

        Пользователь должен предварительно запустить бота (иметь профиль).
        """
        user = await self._users.get_by_username(username.lstrip("@"))
        if user is None:
            raise NotFoundError("Пользователь не найден. Он должен сначала запустить бота.")
        if user.is_staff:
            raise ConflictError("Пользователь уже является сотрудником.")
        role = await self._roles.get(role_id)
        if role is None:
            raise NotFoundError("Должность не найдена.")
        user.is_staff = True
        user.role_id = role.id
        await self._session.flush()
        return user

    async def dismiss(self, user_id: uuid.UUID) -> User:
        """Уволить сотрудника (снять должность)."""
        user = await self._get_staff(user_id)
        user.is_staff = False
        user.role_id = None
        await self._session.flush()
        return user

    async def change_position(self, user_id: uuid.UUID, role_id: uuid.UUID) -> User:
        """Сменить должность сотрудника."""
        user = await self._get_staff(user_id)
        role = await self._roles.get(role_id)
        if role is None:
            raise NotFoundError("Должность не найдена.")
        user.role_id = role.id
        await self._session.flush()
        return user

    async def block(self, user_id: uuid.UUID) -> User:
        """Заблокировать сотрудника."""
        user = await self._get_staff(user_id)
        user.status = AccountStatus.BLOCKED
        await self._session.flush()
        return user

    async def unblock(self, user_id: uuid.UUID) -> User:
        """Разблокировать сотрудника."""
        user = await self._get_staff(user_id)
        user.status = AccountStatus.ACTIVE
        await self._session.flush()
        return user

    async def stats(self, user_id: uuid.UUID) -> StaffStats:
        """Статистика сотрудника: созданные позиции и последняя активность."""
        user = await self._get_staff(user_id)
        positions = int(
            (
                await self._session.execute(
                    select(func.count(Position.id)).where(Position.created_by_id == user_id)
                )
            ).scalar_one()
        )
        return StaffStats(
            positions_created=positions,
            last_activity=dt(user.last_activity_at),
        )

    async def _get_staff(self, user_id: uuid.UUID) -> User:
        user = await self._users.get(user_id)
        if user is None:
            raise NotFoundError("Сотрудник не найден.")
        return user
