from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ActiveSoftDeleteMixin, Base, TimestampMixin


class FeatureDefinition(Base, TimestampMixin, ActiveSoftDeleteMixin):
    __tablename__ = "feature_definitions"
    __table_args__ = (
        Index("ix_feature_definitions_code", "code", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    default_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="online")


class FeatureValue(Base, TimestampMixin):
    __tablename__ = "feature_values"
    __table_args__ = (
        Index("ix_feature_values_feature_window", "feature_definition_id", "window_start", "window_end"),
        Index("ix_feature_values_layer", "storage_layer", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feature_definition_id: Mapped[int] = mapped_column(
        ForeignKey("feature_definitions.id", ondelete="CASCADE"), nullable=False
    )

    object_type: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str] = mapped_column(String(64), nullable=False)

    value_numeric: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    processing_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="online")
    storage_layer: Mapped[str] = mapped_column(String(16), nullable=False, default="hot")

    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    lineage_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lineage_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class FeatureLineage(Base, TimestampMixin):
    __tablename__ = "feature_lineage"
    __table_args__ = (
        Index("ix_feature_lineage_feature_run", "feature_definition_id", "run_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feature_definition_id: Mapped[int] = mapped_column(
        ForeignKey("feature_definitions.id", ondelete="CASCADE"), nullable=False
    )
    feature_value_id: Mapped[int | None] = mapped_column(
        ForeignKey("feature_values.id", ondelete="SET NULL"), nullable=True
    )

    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    transform_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)


class DailyOperationMetric(Base, TimestampMixin):
    __tablename__ = "daily_operation_metrics"
    __table_args__ = (
        Index("ix_daily_operation_metrics_day", "metric_day", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_day: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    transaction_volume: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversion_rate: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False, default=0)
    activity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dispute_rate: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False, default=0)


class OperationConfiguration(Base, TimestampMixin):
    __tablename__ = "operation_configurations"
    __table_args__ = (
        Index("ix_operation_configurations_key_active", "config_key", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_key: Mapped[str] = mapped_column(String(128), nullable=False)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)

    rollout_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    previous_config_id: Mapped[int | None] = mapped_column(
        ForeignKey("operation_configurations.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_rolled_back: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
