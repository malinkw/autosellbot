"""ORM-модели домена. Импорт здесь регистрирует все таблицы в ``Base.metadata``."""

from app.database.base import Base
from app.models.audit import AuditLog
from app.models.bot_settings import BotSetting
from app.models.catalog import Category, Product
from app.models.dispute import (
    Dispute,
    DisputeHistory,
    DisputeMessage,
    DisputeParticipant,
)
from app.models.enums import (
    AccountStatus,
    DisputeActionType,
    DisputeStatus,
    OrderStatus,
    PositionStatus,
    RequisiteType,
    TopUpStatus,
    TransactionType,
)
from app.models.locality import District, Location
from app.models.order import Order, OrderStatusHistory
from app.models.position import Position
from app.models.rbac import PermissionEntity, Role, RolePermission
from app.models.review import Review
from app.models.user import User
from app.models.wallet import Requisite, TopUpRequest, Transaction

__all__ = [
    "AccountStatus",
    "AuditLog",
    "Base",
    "BotSetting",
    "Category",
    "Dispute",
    "DisputeActionType",
    "DisputeHistory",
    "DisputeMessage",
    "DisputeParticipant",
    "DisputeStatus",
    "District",
    "Location",
    "Order",
    "OrderStatus",
    "OrderStatusHistory",
    "PermissionEntity",
    "Position",
    "PositionStatus",
    "Product",
    "Requisite",
    "RequisiteType",
    "Review",
    "Role",
    "RolePermission",
    "TopUpRequest",
    "TopUpStatus",
    "Transaction",
    "TransactionType",
    "User",
]
