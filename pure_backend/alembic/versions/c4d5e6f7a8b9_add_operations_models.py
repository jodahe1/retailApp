"""add operations models

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-03-27 01:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feature_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ttl_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("default_mode", sa.String(length=16), nullable=False, server_default="online"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_feature_definitions_code", "feature_definitions", ["code"], unique=True)

    op.create_table(
        "feature_values",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feature_definition_id", sa.Integer(), nullable=False),
        sa.Column("object_type", sa.String(length=64), nullable=False),
        sa.Column("object_id", sa.String(length=64), nullable=False),
        sa.Column("value_numeric", sa.Numeric(18, 6), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("processing_mode", sa.String(length=16), nullable=False, server_default="online"),
        sa.Column("storage_layer", sa.String(length=16), nullable=False, server_default="hot"),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lineage_source", sa.String(length=255), nullable=True),
        sa.Column("lineage_run_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["feature_definition_id"], ["feature_definitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_feature_values_feature_window",
        "feature_values",
        ["feature_definition_id", "window_start", "window_end"],
        unique=False,
    )
    op.create_index("ix_feature_values_layer", "feature_values", ["storage_layer", "expires_at"], unique=False)

    op.create_table(
        "feature_lineage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("feature_definition_id", sa.Integer(), nullable=False),
        sa.Column("feature_value_id", sa.Integer(), nullable=True),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=False),
        sa.Column("transform_digest", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["feature_definition_id"], ["feature_definitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["feature_value_id"], ["feature_values.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_feature_lineage_feature_run",
        "feature_lineage",
        ["feature_definition_id", "run_id"],
        unique=False,
    )

    op.create_table(
        "daily_operation_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("metric_day", sa.DateTime(timezone=True), nullable=False),
        sa.Column("transaction_volume", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversion_rate", sa.Numeric(8, 6), nullable=False, server_default="0"),
        sa.Column("activity_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dispute_rate", sa.Numeric(8, 6), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_daily_operation_metrics_day", "daily_operation_metrics", ["metric_day"], unique=True)

    op.create_table(
        "operation_configurations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("config_key", sa.String(length=128), nullable=False),
        sa.Column("config_value", sa.Text(), nullable=False),
        sa.Column("rollout_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("previous_config_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_rolled_back", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["previous_config_id"], ["operation_configurations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_operation_configurations_key_active",
        "operation_configurations",
        ["config_key", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_operation_configurations_key_active", table_name="operation_configurations")
    op.drop_table("operation_configurations")

    op.drop_index("ix_daily_operation_metrics_day", table_name="daily_operation_metrics")
    op.drop_table("daily_operation_metrics")

    op.drop_index("ix_feature_lineage_feature_run", table_name="feature_lineage")
    op.drop_table("feature_lineage")

    op.drop_index("ix_feature_values_layer", table_name="feature_values")
    op.drop_index("ix_feature_values_feature_window", table_name="feature_values")
    op.drop_table("feature_values")

    op.drop_index("ix_feature_definitions_code", table_name="feature_definitions")
    op.drop_table("feature_definitions")
