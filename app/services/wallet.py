"""Служба кошелька: атомарные операции с балансом и история.

Все изменения баланса проходят через :meth:`WalletService.apply`, который
блокирует строку пользователя (``SELECT ... FOR UPDATE``) — это защищает от
Race Condition при конкурентных списаниях/начислениях и гарантирует, что
``balance_after`` в журнале операций всегда согласован.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InsufficientFundsError, NotFoundError, ValidationError
from app.models import Transaction, User
from app.models.enums import TransactionType
from app.repositories.wallet import TransactionRepository, WalletUserRepository

ZERO = Decimal("0.00")


class WalletService:
    """Операции с балансом пользователя."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = WalletUserRepository(session)
        self._tx = TransactionRepository(session)

    async def apply(
        self,
        user_id: uuid.UUID,
        *,
        type_: TransactionType,
        amount: Decimal,
        reference: str | None = None,
        comment: str | None = None,
        created_by: User | None = None,
    ) -> Transaction:
        """Атомарно изменить баланс и записать операцию.

        :param amount: знаковая сумма (положительная — начисление, отрицательная — списание).
        :raises InsufficientFundsError: если списание приводит к отрицательному балансу.
        """
        amount = Decimal(amount).quantize(Decimal("0.01"))
        if amount == ZERO:
            raise ValidationError("Сумма операции не может быть нулевой.")

        user = await self._users.lock(user_id)
        if user is None:
            raise NotFoundError("Пользователь не найден.")

        new_balance = (user.balance + amount).quantize(Decimal("0.01"))
        if new_balance < ZERO:
            raise InsufficientFundsError()

        user.balance = new_balance
        transaction = await self._tx.create(
            user_id=user_id,
            type=type_,
            amount=amount,
            balance_after=new_balance,
            reference=reference,
            comment=comment,
            created_by_id=created_by.id if created_by else None,
        )
        await self._session.flush()
        return transaction

    async def credit(
        self,
        user_id: uuid.UUID,
        amount: Decimal,
        *,
        type_: TransactionType,
        reference: str | None = None,
        comment: str | None = None,
        created_by: User | None = None,
    ) -> Transaction:
        """Начислить средства (сумма приводится к положительной)."""
        return await self.apply(
            user_id,
            type_=type_,
            amount=abs(Decimal(amount)),
            reference=reference,
            comment=comment,
            created_by=created_by,
        )

    async def debit(
        self,
        user_id: uuid.UUID,
        amount: Decimal,
        *,
        type_: TransactionType,
        reference: str | None = None,
        comment: str | None = None,
        created_by: User | None = None,
    ) -> Transaction:
        """Списать средства (сумма приводится к отрицательной)."""
        return await self.apply(
            user_id,
            type_=type_,
            amount=-abs(Decimal(amount)),
            reference=reference,
            comment=comment,
            created_by=created_by,
        )

    async def manual_adjust(
        self, user_id: uuid.UUID, amount: Decimal, *, admin: User, comment: str
    ) -> Transaction:
        """Ручная корректировка баланса администратором."""
        return await self.apply(
            user_id,
            type_=TransactionType.MANUAL,
            amount=Decimal(amount),
            comment=comment,
            created_by=admin,
        )

    async def history(self, user_id: uuid.UUID, *, limit: int | None = None) -> list[Transaction]:
        """История операций пользователя."""
        return await self._tx.for_user(user_id, limit=limit)
