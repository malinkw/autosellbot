"""Репозитории местности: районы и локации."""

from __future__ import annotations

from app.models import District, Location
from app.repositories.base import BaseRepository


class DistrictRepository(BaseRepository[District]):
    """Доступ к районам."""

    model = District

    async def active(self) -> list[District]:
        """Активные районы."""
        return await self.list(filters=[District.is_active.is_(True)], order_by=[District.name])


class LocationRepository(BaseRepository[Location]):
    """Доступ к кастомным локациям."""

    model = Location

    async def active(self) -> list[Location]:
        """Активные локации."""
        return await self.list(filters=[Location.is_active.is_(True)], order_by=[Location.name])
