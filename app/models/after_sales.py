from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AfterSalesType(StrEnum):
    RETURN = "return"
    EXCHANGE = "exchange"
    REFUND = "refund"


class AfterSalesStatus(StrEnum):
    CREATED = "created"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class AfterSalesOrder(Base, TimestampMixin):
    __tablename__ = "after_sales_orders"
    __table_args__ = (
        Index("ix_after_sales_orders_original_order_id", "original_order_id"),
        Index("ix_after_sales_orders_type_status", "after_sales_type", "status"),
        UniqueConstraint("idempotency_key", name="uq_after_sales_orders_idempotency_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False)
    staff_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    after_sales_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=AfterSalesStatus.CREATED)

    requested_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    approved_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
