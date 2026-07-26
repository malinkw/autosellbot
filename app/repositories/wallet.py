"""Репозитории кошелька: операции, заявки, реквизиты."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.models import Requisite, TopUpRequest, Transaction, User
from app.models.enums import TopUpStatus, TransactionType
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """Доступ к операциям по балансу."""

    model = Transaction

    async def for_user(self, user_id: uuid.UUID, *, limit: int | None = None) -> list[Transaction]:
        """История операций пользователя."""
        return await self.list(
            filters=[Transaction.user_id == user_id],
            order_by=[Transaction.created_at.desc()],
            limit=limit,
        )

    async def sum_by_type(
        self,
        type_: TransactionType,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> Decimal:
        """Сумма модулей операций указанного типа за период."""
        stmt = select(func.coalesce(func.sum(func.abs(Transaction.amount)), 0)).where(
            Transaction.type == type_
        )
        if since is not None:
            stmt = stmt.where(Transaction.created_at >= since)
        if until is not None:
            stmt = stmt.where(Transaction.created_at < until)
        return Decimal((await self.session.execute(stmt)).scalar_one())


class TopUpRepository(BaseRepository[TopUpRequest]):
    """Доступ к заявкам на пополнение."""

    model = TopUpRequest

    async def get_by_number(self, number: str) -> TopUpRequest | None:
        """Найти заявку по номеру."""
        return await self.get_by(number=number)

    async def for_user(self, user_id: uuid.UUID) -> list[TopUpRequest]:
        """Заявки пользователя."""
        return await self.list(
            filters=[TopUpRequest.user_id == user_id],
            order_by=[TopUpRequest.created_at.desc()],
        )

    async def pending(self) -> list[TopUpRequest]:
        """Заявки, ожидающие обработки."""
        return await self.list(
            filters=[TopUpRequest.status.in_([TopUpStatus.CREATED, TopUpStatus.CHECKING])],
            order_by=[TopUpRequest.created_at],
        )


class RequisiteRepository(BaseRepository[Requisite]):
    """Доступ к платёжным реквизитам."""

    model = Requisite

    async def active(self) -> list[Requisite]:
        """Активные реквизиты в порядке приоритета."""
        return await self.list(
            filters=[Requisite.is_active.is_(True)],
            order_by=[Requisite.priority.desc(), Requisite.created_at],
        )

    async def all_ordered(self) -> list[Requisite]:
        """Все реквизиты в порядке приоритета."""
        return await self.list(order_by=[Requisite.priority.desc(), Requisite.created_at])


class WalletUserRepository(BaseRepository[User]):
    """Доступ к пользователю с блокировкой строки баланса (защита от Race Condition)."""

    model = User

    async def lock(self, user_id: uuid.UUID) -> User | None:
        """Загрузить пользователя с ``SELECT ... FOR UPDATE`` для операций с балансом."""
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None)).with_for_update()
        return (await self.session.execute(stmt)).scalars().first()
