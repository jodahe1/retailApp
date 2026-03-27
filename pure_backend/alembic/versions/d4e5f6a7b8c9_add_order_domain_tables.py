"""add order domain tables

Revision ID: d4e5f6a7b8c9
Revises: c3f1d2a4b5e6
Create Date: 2026-03-26 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3f1d2a4b5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column("cashier_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("subtotal_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("item_discount_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("order_discount_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("promotion_discount_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("final_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cashier_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_no"),
    )
    op.create_index("ix_orders_order_no", "orders", ["order_no"], unique=True)
    op.create_index("ix_orders_status_created", "orders", ["status", "created_at"], unique=False)

    op.create_table(
        "order_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=255), nullable=False),
        sa.Column("product_barcode_snapshot", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("item_discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("promotion_discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("final_line_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_lines_order_id", "order_lines", ["order_id"], unique=False)
    op.create_index("ix_order_lines_product_id", "order_lines", ["product_id"], unique=False)

    op.create_table(
        "promotion_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("rule_type", sa.String(length=32), nullable=False),
        sa.Column("threshold_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("buy_quantity", sa.Integer(), nullable=True),
        sa.Column("get_quantity", sa.Integer(), nullable=True),
        sa.Column("tier_quantity", sa.Integer(), nullable=True),
        sa.Column("tier_unit_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("purchase_limit_quantity", sa.Integer(), nullable=True),
        sa.Column("applies_to_product_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["applies_to_product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_promotion_rules_type_active", "promotion_rules", ["rule_type", "is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_promotion_rules_type_active", table_name="promotion_rules")
    op.drop_table("promotion_rules")

    op.drop_index("ix_order_lines_product_id", table_name="order_lines")
    op.drop_index("ix_order_lines_order_id", table_name="order_lines")
    op.drop_table("order_lines")

    op.drop_index("ix_orders_status_created", table_name="orders")
    op.drop_index("ix_orders_order_no", table_name="orders")
    op.drop_table("orders")
