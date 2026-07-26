"""Репозитории диспутов."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models import (
    Dispute,
    DisputeHistory,
    DisputeMessage,
    DisputeParticipant,
)
from app.repositories.base import BaseRepository


class DisputeRepository(BaseRepository[Dispute]):
    """Доступ к диспутам."""

    model = Dispute

    async def get_by_number(self, number: str) -> Dispute | None:
        """Найти диспут по номеру."""
        return await self.get_by(number=number)

    async def get_by_order(self, order_id: uuid.UUID) -> Dispute | None:
        """Найти диспут по заказу."""
        return await self.get_by(order_id=order_id)

    async def for_participant(self, user_id: uuid.UUID) -> list[Dispute]:
        """Диспуты, в которых пользователь является участником."""
        stmt = (
            select(Dispute)
            .join(DisputeParticipant, DisputeParticipant.dispute_id == Dispute.id)
            .where(DisputeParticipant.user_id == user_id, Dispute.deleted_at.is_(None))
            .order_by(Dispute.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().unique().all())


class DisputeParticipantRepository(BaseRepository[DisputeParticipant]):
    """Доступ к участникам диспутов."""

    model = DisputeParticipant

    async def is_participant(self, dispute_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Является ли пользователь участником диспута."""
        return await self.exists(dispute_id=dispute_id, user_id=user_id)


class DisputeMessageRepository(BaseRepository[DisputeMessage]):
    """Доступ к сообщениям диспутов."""

    model = DisputeMessage


class DisputeHistoryRepository(BaseRepository[DisputeHistory]):
    """Доступ к неизменяемой истории диспутов."""

    model = DisputeHistory

    async def for_dispute(self, dispute_id: uuid.UUID) -> list[DisputeHistory]:
        """Полная история действий по диспуту."""
        return await self.list(
            filters=[DisputeHistory.dispute_id == dispute_id],
            order_by=[DisputeHistory.created_at],
        )
