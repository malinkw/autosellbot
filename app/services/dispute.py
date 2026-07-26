"""Служба диспутов.

Реализует требования ТЗ: окно 24 часа после завершения заказа, автоматический
подбор участников (сотрудники с правами просмотра/ответа/закрытия/управления
диспутами + создатель позиции, он же ответственный по умолчанию), неизменяемую
историю всех действий, а также действия участников, каждое из которых защищено
отдельным правом на уровне хендлеров.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import (
    Dispute,
    DisputeHistory,
    DisputeMessage,
    DisputeParticipant,
    User,
)
from app.models.enums import (
    DisputeActionType,
    DisputeStatus,
    OrderStatus,
    TransactionType,
)
from app.permissions import PERMISSION_METADATA
from app.permissions.registry import DISPUTE_PARTICIPANT_PERMISSIONS
from app.repositories.dispute import (
    DisputeHistoryRepository,
    DisputeParticipantRepository,
    DisputeRepository,
)
from app.repositories.order import OrderRepository
from app.repositories.position import PositionRepository
from app.repositories.user import UserRepository
from app.services.wallet import WalletService
from app.utils.ids import generate_number


@dataclass(slots=True)
class DisputeCreation:
    """Результат создания диспута — сам диспут и участники для уведомления."""

    dispute: Dispute
    participants: list[User] = field(default_factory=list)


class DisputeService:
    """Бизнес-логика диспутов."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._disputes = DisputeRepository(session)
        self._participants = DisputeParticipantRepository(session)
        self._history = DisputeHistoryRepository(session)
        self._orders = OrderRepository(session)
        self._positions = PositionRepository(session)
        self._users = UserRepository(session)
        self._wallet = WalletService(session)

    async def open(self, opener: User, order_id: uuid.UUID, subject: str) -> DisputeCreation:
        """Открыть диспут по завершённому заказу (не позднее окна из настроек)."""
        order = await self._orders.get(order_id)
        if order is None or order.user_id != opener.id:
            raise NotFoundError("Заказ не найден.")
        if order.status != OrderStatus.COMPLETED or order.completed_at is None:
            raise BusinessRuleError("Диспут можно открыть только по завершённому заказу.")

        window = timedelta(hours=self._settings.app.dispute_window_hours)
        if datetime.now(UTC) - order.completed_at > window:
            raise BusinessRuleError(
                f"Срок открытия диспута истёк ({self._settings.app.dispute_window_hours} ч)."
            )
        if await self._disputes.get_by_order(order.id) is not None:
            raise ConflictError("Диспут по этому заказу уже открыт.")

        dispute = await self._disputes.create(
            number=generate_number("DSP"),
            order_id=order.id,
            opener_id=opener.id,
            subject=subject.strip() or "Без описания",
            status=DisputeStatus.OPEN,
        )
        await self._log(dispute, DisputeActionType.CREATED, opener, "Диспут открыт")

        participants = await self._auto_participants(order, dispute)

        # Ответственный по умолчанию — создатель позиции.
        creator = await self._position_creator(order)
        if creator is not None:
            dispute.responsible_id = creator.id
            await self._log(
                dispute,
                DisputeActionType.RESPONSIBLE_ASSIGNED,
                None,
                f"Ответственный назначен: {creator.public_id}",
            )
        await self._session.flush()
        return DisputeCreation(dispute=dispute, participants=participants)

    async def _position_creator(self, order: object) -> User | None:
        position_id = getattr(order, "position_id", None)
        if position_id is None:
            return None
        position = await self._positions.get(position_id)
        if position is None or position.created_by_id is None:
            return None
        return await self._users.get(position.created_by_id)

    async def _auto_participants(self, order: object, dispute: Dispute) -> list[User]:
        """Подобрать и зафиксировать автоматических участников диспута."""
        collected: dict[uuid.UUID, str] = {}

        for permission in DISPUTE_PARTICIPANT_PERMISSIONS:
            title = PERMISSION_METADATA[permission].title
            for staff in await self._users.staff_with_permission(permission.value):
                collected.setdefault(staff.id, f"Право: {title}")

        creator = await self._position_creator(order)
        if creator is not None:
            collected[creator.id] = "Создатель позиции"

        users: list[User] = []
        for user_id, reason in collected.items():
            self._session.add(
                DisputeParticipant(
                    dispute_id=dispute.id,
                    user_id=user_id,
                    reason=reason,
                    auto_added=True,
                )
            )
            await self._log(
                dispute,
                DisputeActionType.PARTICIPANT_ADDED,
                None,
                f"Добавлен участник {user_id} ({reason})",
            )
            user = await self._users.get(user_id)
            if user is not None:
                users.append(user)
        return users

    async def get(self, dispute_id: uuid.UUID) -> Dispute:
        dispute = await self._disputes.get(dispute_id)
        if dispute is None:
            raise NotFoundError("Диспут не найден.")
        return dispute

    async def reply(
        self, dispute_id: uuid.UUID, sender: User, *, text: str | None, file_id: str | None
    ) -> DisputeMessage:
        """Добавить сообщение в переписку диспута."""
        dispute = await self.get(dispute_id)
        if dispute.status in {DisputeStatus.CLOSED, DisputeStatus.REFUNDED}:
            raise BusinessRuleError("Диспут закрыт для новых сообщений.")
        message = DisputeMessage(
            dispute_id=dispute.id, sender_id=sender.id, text=text, file_id=file_id
        )
        self._session.add(message)
        await self._log(dispute, DisputeActionType.MESSAGE, sender, text or "[вложение]")
        await self._session.flush()
        return message

    async def change_status(
        self, dispute_id: uuid.UUID, status: DisputeStatus, *, actor: User
    ) -> Dispute:
        """Изменить статус диспута."""
        dispute = await self.get(dispute_id)
        old = dispute.status
        dispute.status = status
        await self._log(
            dispute,
            DisputeActionType.STATUS_CHANGED,
            actor,
            f"{old} → {status}",
        )
        await self._session.flush()
        return dispute

    async def assign_responsible(
        self, dispute_id: uuid.UUID, new_responsible: User, *, actor: User
    ) -> Dispute:
        """Сменить ответственного (право ``disputes.assign_responsible``)."""
        dispute = await self.get(dispute_id)
        dispute.responsible_id = new_responsible.id
        if not await self._participants.is_participant(dispute.id, new_responsible.id):
            self._session.add(
                DisputeParticipant(
                    dispute_id=dispute.id,
                    user_id=new_responsible.id,
                    reason="Назначен ответственным",
                    auto_added=False,
                )
            )
        await self._log(
            dispute,
            DisputeActionType.RESPONSIBLE_CHANGED,
            actor,
            f"Новый ответственный: {new_responsible.public_id}",
        )
        await self._session.flush()
        return dispute

    async def transfer(self, dispute_id: uuid.UUID, target: User, *, actor: User) -> Dispute:
        """Передать диспут другому сотруднику (добавляет его в участники)."""
        dispute = await self.get(dispute_id)
        if not await self._participants.is_participant(dispute.id, target.id):
            self._session.add(
                DisputeParticipant(
                    dispute_id=dispute.id,
                    user_id=target.id,
                    reason="Передача диспута",
                    auto_added=False,
                )
            )
        await self._log(
            dispute,
            DisputeActionType.TRANSFERRED,
            actor,
            f"Передан сотруднику {target.public_id}",
        )
        await self._session.flush()
        return dispute

    async def close(self, dispute_id: uuid.UUID, *, actor: User, resolution: str) -> Dispute:
        """Закрыть диспут с указанием решения."""
        dispute = await self.get(dispute_id)
        dispute.status = DisputeStatus.CLOSED
        dispute.resolution = resolution
        dispute.closed_at = datetime.now(UTC)
        await self._log(dispute, DisputeActionType.CLOSED, actor, resolution)
        await self._session.flush()
        return dispute

    async def reopen(self, dispute_id: uuid.UUID, *, actor: User) -> Dispute:
        """Повторно открыть закрытый диспут."""
        dispute = await self.get(dispute_id)
        if dispute.status not in {DisputeStatus.CLOSED, DisputeStatus.RESOLVED}:
            raise BusinessRuleError("Повторно открыть можно только закрытый диспут.")
        dispute.status = DisputeStatus.OPEN
        dispute.closed_at = None
        await self._log(dispute, DisputeActionType.REOPENED, actor, "Диспут переоткрыт")
        await self._session.flush()
        return dispute

    async def refund(
        self, dispute_id: uuid.UUID, *, actor: User, comment: str | None = None
    ) -> Dispute:
        """Оформить возврат в рамках диспута."""
        dispute = await self.get(dispute_id)
        order = await self._orders.get(dispute.order_id)
        if order is None:
            raise NotFoundError("Заказ диспута не найден.")
        if order.status == OrderStatus.REFUNDED:
            raise BusinessRuleError("Возврат по заказу уже оформлен.")
        await self._wallet.credit(
            order.user_id,
            Decimal(order.amount),
            type_=TransactionType.REFUND,
            reference=order.number,
            comment=comment or f"Возврат по диспуту {dispute.number}",
            created_by=actor,
        )
        order.status = OrderStatus.REFUNDED
        dispute.status = DisputeStatus.REFUNDED
        await self._log(dispute, DisputeActionType.REFUNDED, actor, comment or "Возврат оформлен")
        await self._session.flush()
        return dispute

    async def history(self, dispute_id: uuid.UUID) -> list[DisputeHistory]:
        """Полная неизменяемая история диспута."""
        return await self._history.for_dispute(dispute_id)

    async def for_participant(self, user_id: uuid.UUID) -> list[Dispute]:
        """Диспуты, где пользователь — участник."""
        return await self._disputes.for_participant(user_id)

    async def get_for_order(self, order_id: uuid.UUID) -> Dispute | None:
        """Диспут по заказу (если открыт)."""
        return await self._disputes.get_by_order(order_id)

    async def for_opener(self, user_id: uuid.UUID) -> list[Dispute]:
        """Диспуты, открытые пользователем."""
        return await self._disputes.list(
            filters=[Dispute.opener_id == user_id],
            order_by=[Dispute.created_at.desc()],
        )

    async def all_disputes(self) -> list[Dispute]:
        """Все диспуты (для админ-панели)."""
        return await self._disputes.list(order_by=[Dispute.created_at.desc()])

    async def _log(
        self,
        dispute: Dispute,
        action: DisputeActionType,
        actor: User | None,
        details: str | None,
    ) -> DisputeHistory:
        entry = DisputeHistory(
            dispute_id=dispute.id,
            actor_id=actor.id if actor else None,
            action=action,
            details=details,
        )
        self._session.add(entry)
        return entry
