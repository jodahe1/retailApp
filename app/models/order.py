from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class OrderStatus(StrEnum):
    PENDING = "pending"
    PARTIALLY_PAID = "partially_paid"
    SETTLED = "settled"
    VOID = "void"


class PromotionType(StrEnum):
    SPEND_AND_SAVE = "spend_and_save"
    BUY_AND_GET = "buy_and_get"
    TIERED_PRICING = "tiered_pricing"
    PURCHASE_LIMIT = "purchase_limit"


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_order_no", "order_no", unique=True),
        Index("ix_orders_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    cashier_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    status: Mapped[str] = mapped_column(String(24), nullable=False, default=OrderStatus.PENDING)

    subtotal_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    item_discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    order_discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    promotion_discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    final_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    void_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    lines: Mapped[list[OrderLine]] = relationship("OrderLine", back_populates="order", cascade="all, delete-orphan")


class OrderLine(Base, TimestampMixin):
    __tablename__ = "order_lines"
    __table_args__ = (
        Index("ix_order_lines_order_id", "order_id"),
        Index("ix_order_lines_product_id", "product_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    product_barcode_snapshot: Mapped[str] = mapped_column(String(64), nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    line_subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    item_discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    promotion_discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    final_line_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    order: Mapped[Order] = relationship("Order", back_populates="lines")


class PromotionRule(Base, TimestampMixin):
    __tablename__ = "promotion_rules"
    __table_args__ = (Index("ix_promotion_rules_type_active", "rule_type", "is_active"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)

    threshold_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    buy_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    get_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    tier_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tier_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    purchase_limit_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    applies_to_product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
