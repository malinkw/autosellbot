"""Служба заявок на пополнение баланса."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BusinessRuleError, NotFoundError, ValidationError
from app.models import TopUpRequest, User
from app.models.enums import TopUpStatus, TransactionType
from app.repositories.wallet import TopUpRepository
from app.services.wallet import WalletService
from app.utils.ids import generate_number


class TopUpService:
    """Бизнес-логика пополнения кошелька."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TopUpRepository(session)
        self._wallet = WalletService(session)

    async def create(
        self,
        user: User,
        amount: Decimal,
        *,
        receipt_file_id: str | None = None,
        receipt_file_name: str | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
    ) -> TopUpRequest:
        """Создать заявку на пополнение с прикреплённым PDF-чеком."""
        amount = Decimal(amount)
        if amount <= 0:
            raise ValidationError("Сумма пополнения должна быть больше нуля.")
        if min_amount is not None and amount < min_amount:
            raise ValidationError(f"Минимальная сумма пополнения: {min_amount}.")
        if max_amount is not None and amount > max_amount:
            raise ValidationError(f"Максимальная сумма пополнения: {max_amount}.")

        return await self._repo.create(
            number=generate_number("TOP"),
            user_id=user.id,
            amount=amount,
            receipt_file_id=receipt_file_id,
            receipt_file_name=receipt_file_name,
            status=TopUpStatus.CREATED,
        )

    async def get(self, request_id: uuid.UUID) -> TopUpRequest:
        request = await self._repo.get(request_id)
        if request is None:
            raise NotFoundError("Заявка не найдена.")
        return request

    async def pending(self) -> list[TopUpRequest]:
        """Заявки, ожидающие обработки."""
        return await self._repo.pending()

    async def for_user(self, user_id: uuid.UUID) -> list[TopUpRequest]:
        """Заявки пользователя."""
        return await self._repo.for_user(user_id)

    async def set_checking(self, request_id: uuid.UUID) -> TopUpRequest:
        """Перевести заявку в статус «Проверяется»."""
        request = await self.get(request_id)
        request.status = TopUpStatus.CHECKING
        await self._session.flush()
        return request

    async def approve(self, request_id: uuid.UUID, *, admin: User) -> TopUpRequest:
        """Подтвердить заявку: начислить баланс автоматически."""
        request = await self.get(request_id)
        if request.status == TopUpStatus.APPROVED:
            raise BusinessRuleError("Заявка уже подтверждена.")
        if request.status == TopUpStatus.REJECTED:
            raise BusinessRuleError("Отклонённую заявку нельзя подтвердить.")

        await self._wallet.credit(
            request.user_id,
            request.amount,
            type_=TransactionType.TOPUP,
            reference=request.number,
            comment=f"Пополнение по заявке {request.number}",
            created_by=admin,
        )
        request.status = TopUpStatus.APPROVED
        request.processed_by_id = admin.id
        request.processed_at = datetime.now(UTC)
        await self._session.flush()
        return request

    async def reject(
        self, request_id: uuid.UUID, *, admin: User, comment: str | None = None
    ) -> TopUpRequest:
        """Отклонить заявку."""
        request = await self.get(request_id)
        if request.status == TopUpStatus.APPROVED:
            raise BusinessRuleError("Подтверждённую заявку нельзя отклонить.")
        request.status = TopUpStatus.REJECTED
        request.comment = comment
        request.processed_by_id = admin.id
        request.processed_at = datetime.now(UTC)
        await self._session.flush()
        return request

    async def comment(self, request_id: uuid.UUID, text: str) -> TopUpRequest:
        """Оставить комментарий к заявке."""
        request = await self.get(request_id)
        request.comment = text
        await self._session.flush()
        return request
