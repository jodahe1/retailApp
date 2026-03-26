from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PaymentMethod(StrEnum):
    CASH = "cash"
    BANK_CARD = "bank_card"
    STORED_VALUE = "stored_value"


class PaymentStatus(StrEnum):
    COMPLETED = "completed"


class PaymentRecord(Base, TimestampMixin):
    __tablename__ = "payment_records"
    __table_args__ = (
        Index("ix_payment_records_order_id", "order_id"),
        Index("ix_payment_records_order_method", "order_id", "method"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    cashier_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    method: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=PaymentStatus.COMPLETED)

    offline_approval_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
