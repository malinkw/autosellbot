"""Контейнер сервисов: единая точка доступа к бизнес-логике внутри одной сессии БД.

Создаётся в middleware на каждый апдейт и передаётся в хендлеры. Ленивая
инициализация служб исключает лишнюю работу для простых обработчиков.
"""

from __future__ import annotations

from functools import cached_property

from aiogram import Bot
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.services.accounting import AccountingService
from app.services.audit import AuditService
from app.services.backup import BackupService
from app.services.catalog import CatalogService
from app.services.dispute import DisputeService
from app.services.export import ExportService
from app.services.locality import LocalityService
from app.services.notification import NotificationService
from app.services.order import OrderService
from app.services.permission import PermissionService
from app.services.position import PositionService
from app.services.requisite import RequisiteService
from app.services.review import ReviewService
from app.services.role import RoleService
from app.services.settings_service import SettingsService
from app.services.staff import StaffService
from app.services.topup import TopUpService
from app.services.user import UserService
from app.services.wallet import WalletService
from app.utils.security import IdempotencyGuard


class ServiceContainer:
    """Агрегатор служб, работающих в рамках одной транзакции."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        *,
        redis: Redis,
        bot: Bot,
    ) -> None:
        self.session = session
        self.settings = settings
        self.redis = redis
        self.bot = bot

    @cached_property
    def permissions(self) -> PermissionService:
        return PermissionService(self.settings)

    @cached_property
    def audit(self) -> AuditService:
        return AuditService(self.session)

    @cached_property
    def users(self) -> UserService:
        return UserService(self.session)

    @cached_property
    def catalog(self) -> CatalogService:
        return CatalogService(self.session)

    @cached_property
    def positions(self) -> PositionService:
        return PositionService(self.session)

    @cached_property
    def locality(self) -> LocalityService:
        return LocalityService(self.session)

    @cached_property
    def orders(self) -> OrderService:
        return OrderService(self.session)

    @cached_property
    def wallet(self) -> WalletService:
        return WalletService(self.session)

    @cached_property
    def topups(self) -> TopUpService:
        return TopUpService(self.session)

    @cached_property
    def disputes(self) -> DisputeService:
        return DisputeService(self.session, self.settings)

    @cached_property
    def reviews(self) -> ReviewService:
        return ReviewService(self.session)

    @cached_property
    def staff(self) -> StaffService:
        return StaffService(self.session)

    @cached_property
    def roles(self) -> RoleService:
        return RoleService(self.session)

    @cached_property
    def accounting(self) -> AccountingService:
        return AccountingService(self.session)

    @cached_property
    def requisites(self) -> RequisiteService:
        return RequisiteService(self.session)

    @cached_property
    def bot_settings(self) -> SettingsService:
        return SettingsService(self.session)

    @cached_property
    def export(self) -> ExportService:
        return ExportService(self.session)

    @cached_property
    def backup(self) -> BackupService:
        return BackupService(self.settings)

    @cached_property
    def notifications(self) -> NotificationService:
        return NotificationService(self.bot)

    @cached_property
    def idempotency(self) -> IdempotencyGuard:
        return IdempotencyGuard(self.redis)
