"""Import models here for SQLAlchemy metadata discovery and Alembic autogenerate."""

from app.models.after_sales import AfterSalesOrder
from app.models.attachment import Attachment
from app.models.identity import (
    ImmutableAuditLog,
    Permission,
    Role,
    RolePermission,
    SensitiveAccessLog,
    SessionToken,
    User,
    UserRole,
)
from app.models.notification import Notification, NotificationSubscription
from app.models.order import Order, OrderLine, PromotionRule
from app.models.payment import PaymentRecord
from app.models.product import Product
from app.models.project import Project, ProjectVersion

__all__ = [
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    "SessionToken",
    "SensitiveAccessLog",
    "ImmutableAuditLog",
    "Product",
    "Order",
    "OrderLine",
    "PromotionRule",
    "PaymentRecord",
    "AfterSalesOrder",
    "Project",
    "ProjectVersion",
    "Attachment",
    "Notification",
    "NotificationSubscription",
]
