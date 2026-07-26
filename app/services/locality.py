"""Служба местности: районы и кастомные локации."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError, ValidationError
from app.models import District, Location
from app.repositories.locality import DistrictRepository, LocationRepository


class LocalityService:
    """CRUD районов и локаций."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._districts = DistrictRepository(session)
        self._locations = LocationRepository(session)

    # --- Районы --------------------------------------------------------------
    async def list_districts(self, *, active_only: bool = False) -> list[District]:
        """Список районов."""
        if active_only:
            return await self._districts.active()
        return await self._districts.list(order_by=[District.name])

    async def create_district(self, name: str) -> District:
        """Создать район."""
        if not name.strip():
            raise ValidationError("Название района не может быть пустым.")
        return await self._districts.create(name=name.strip())

    async def get_district(self, district_id: uuid.UUID) -> District:
        district = await self._districts.get(district_id)
        if district is None:
            raise NotFoundError("Район не найден.")
        return district

    async def update_district(self, district_id: uuid.UUID, **values: object) -> District:
        """Обновить район."""
        district = await self.get_district(district_id)
        return await self._districts.update(district, **values)

    async def delete_district(self, district_id: uuid.UUID) -> None:
        """Мягко удалить район."""
        district = await self.get_district(district_id)
        await self._districts.soft_delete(district)

    # --- Локации -------------------------------------------------------------
    async def list_locations(self, *, active_only: bool = False) -> list[Location]:
        """Список локаций."""
        if active_only:
            return await self._locations.active()
        return await self._locations.list(order_by=[Location.name])

    async def create_location(self, name: str, *, description: str | None = None) -> Location:
        """Создать локацию."""
        if not name.strip():
            raise ValidationError("Название локации не может быть пустым.")
        return await self._locations.create(name=name.strip(), description=description)

    async def get_location(self, location_id: uuid.UUID) -> Location:
        location = await self._locations.get(location_id)
        if location is None:
            raise NotFoundError("Локация не найдена.")
        return location

    async def update_location(self, location_id: uuid.UUID, **values: object) -> Location:
        """Обновить локацию."""
        location = await self.get_location(location_id)
        return await self._locations.update(location, **values)

    async def delete_location(self, location_id: uuid.UUID) -> None:
        """Мягко удалить локацию."""
        location = await self.get_location(location_id)
        await self._locations.soft_delete(location)
