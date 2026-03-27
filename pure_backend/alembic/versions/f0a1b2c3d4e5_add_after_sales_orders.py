"""add after sales orders

Revision ID: f0a1b2c3d4e5
Revises: e7f8a9b0c1d2
Create Date: 2026-03-27 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "after_sales_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("original_order_id", sa.Integer(), nullable=False),
        sa.Column("staff_user_id", sa.Integer(), nullable=False),
        sa.Column("after_sales_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("approved_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["original_order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["staff_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_after_sales_orders_idempotency_key"),
    )
    op.create_index("ix_after_sales_orders_original_order_id", "after_sales_orders", ["original_order_id"], unique=False)
    op.create_index("ix_after_sales_orders_type_status", "after_sales_orders", ["after_sales_type", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_after_sales_orders_type_status", table_name="after_sales_orders")
    op.drop_index("ix_after_sales_orders_original_order_id", table_name="after_sales_orders")
    op.drop_table("after_sales_orders")
