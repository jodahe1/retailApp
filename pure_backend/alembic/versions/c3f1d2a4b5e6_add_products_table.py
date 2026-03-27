"""add products table

Revision ID: c3f1d2a4b5e6
Revises: 8d66e8c71a00
Create Date: 2026-03-26 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3f1d2a4b5e6"
down_revision: Union[str, Sequence[str], None] = "8d66e8c71a00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_pinyin", sa.String(length=255), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=False),
        sa.Column("internal_code", sa.String(length=64), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("is_available_for_sale", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_pos_visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("barcode"),
        sa.UniqueConstraint("internal_code"),
    )

    op.create_index("ix_products_id", "products", ["id"], unique=False)
    op.create_index("ix_products_name_pinyin", "products", ["name_pinyin"], unique=False)
    op.create_index("ix_products_barcode", "products", ["barcode"], unique=True)
    op.create_index("ix_products_internal_code", "products", ["internal_code"], unique=True)
    op.create_index(
        "ix_products_quick_match",
        "products",
        ["barcode", "internal_code", "name_pinyin"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_products_quick_match", table_name="products")
    op.drop_index("ix_products_internal_code", table_name="products")
    op.drop_index("ix_products_barcode", table_name="products")
    op.drop_index("ix_products_name_pinyin", table_name="products")
    op.drop_index("ix_products_id", table_name="products")
    op.drop_table("products")
