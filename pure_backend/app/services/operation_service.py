from __future__ import annotations

import csv
import hashlib
import io
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import transactional_session
from app.exceptions.base import AuthorizationException, NotFoundException, ValidationException
from app.models.identity import User
from app.models.operation import (
    DailyOperationMetric,
    FeatureDefinition,
    FeatureLineage,
    FeatureValue,
    OperationConfiguration,
)
from app.schemas.operation import (
    ConsistencyCheckResponse,
    DailyAnalyticsBuildRequest,
    DailyAnalyticsResponse,
    FeatureDefinitionCreateRequest,
    FeatureDefinitionResponse,
    FeatureValueResponse,
    FeatureValueUpsertRequest,
    OperationConfigCreateRequest,
    OperationConfigResponse,
)
from app.security.audit import write_audit_log
from app.security.tokens import utcnow


def _perm_codes(actor: User) -> set[str]:
    return {p.code for r in actor.roles for p in r.permissions}


def _assert_ops_admin(actor: User) -> None:
    if actor.is_superuser:
        return
    if "operations:admin" not in _perm_codes(actor):
        raise AuthorizationException("Operation administrator permission required")


def _feature_def_to_response(entity: FeatureDefinition) -> FeatureDefinitionResponse:
    return FeatureDefinitionResponse(
        id=entity.id,
        code=entity.code,
        name=entity.name,
        description=entity.description,
        ttl_seconds=entity.ttl_seconds,
        default_mode=entity.default_mode,
        created_at=entity.created_at,
    )


def _feature_value_to_response(entity: FeatureValue) -> FeatureValueResponse:
    return FeatureValueResponse(
        id=entity.id,
        feature_definition_id=entity.feature_definition_id,
        object_type=entity.object_type,
        object_id=entity.object_id,
        value_numeric=float(entity.value_numeric) if entity.value_numeric is not None else None,
        value_text=entity.value_text,
        processing_mode=entity.processing_mode,
        storage_layer=entity.storage_layer,
        expires_at=entity.expires_at,
        lineage_source=entity.lineage_source,
        lineage_run_id=entity.lineage_run_id,
        created_at=entity.created_at,
    )


def _config_to_response(entity: OperationConfiguration) -> OperationConfigResponse:
    return OperationConfigResponse(
        id=entity.id,
        config_key=entity.config_key,
        config_value=entity.config_value,
        rollout_percent=entity.rollout_percent,
        version=entity.version,
        previous_config_id=entity.previous_config_id,
        is_active=entity.is_active,
        is_rolled_back=entity.is_rolled_back,
        changed_by_user_id=entity.changed_by_user_id,
        created_at=entity.created_at,
    )


def create_feature_definition(db: Session, actor: User, payload: FeatureDefinitionCreateRequest) -> FeatureDefinitionResponse:
    _assert_ops_admin(actor)

    existing = db.scalar(select(FeatureDefinition).where(FeatureDefinition.code == payload.code))
    if existing is not None:
        raise ValidationException("Feature code already exists")

    with transactional_session(db):
        entity = FeatureDefinition(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            ttl_seconds=payload.ttl_seconds,
            default_mode=payload.default_mode,
            is_active=True,
            is_deleted=False,
        )
        db.add(entity)
        db.flush()

    return _feature_def_to_response(entity)


def _storage_layer(expires_at) -> str:
    return "hot" if expires_at > utcnow() else "cold"


def upsert_feature_value(db: Session, actor: User, payload: FeatureValueUpsertRequest) -> FeatureValueResponse:
    _assert_ops_admin(actor)

    feature = db.scalar(select(FeatureDefinition).where(FeatureDefinition.code == payload.feature_code))
    if feature is None:
        raise NotFoundException("Feature definition not found")

    now = utcnow()
    expires_at = now + timedelta(seconds=feature.ttl_seconds)

    with transactional_session(db):
        entity = FeatureValue(
            feature_definition_id=feature.id,
            object_type=payload.object_type,
            object_id=payload.object_id,
            value_numeric=payload.value_numeric,
            value_text=payload.value_text,
            processing_mode=payload.processing_mode or feature.default_mode,
            storage_layer=_storage_layer(expires_at),
            window_start=now - timedelta(seconds=feature.ttl_seconds),
            window_end=now,
            expires_at=expires_at,
            lineage_source=payload.lineage_source,
            lineage_run_id=payload.lineage_run_id,
        )
        db.add(entity)
        db.flush()

        if payload.lineage_run_id and payload.lineage_source:
            lineage = FeatureLineage(
                feature_definition_id=feature.id,
                feature_value_id=entity.id,
                run_id=payload.lineage_run_id,
                source_type=payload.lineage_source,
                source_reference=f"{payload.object_type}:{payload.object_id}",
                transform_digest=hashlib.sha256(
                    f"{payload.feature_code}:{payload.object_type}:{payload.object_id}:{payload.value_numeric}:{payload.value_text}".encode(
                        "utf-8"
                    )
                ).hexdigest(),
            )
            db.add(lineage)

    return _feature_value_to_response(entity)


def sliding_window_average(
    db: Session,
    actor: User,
    feature_code: str,
    object_type: str,
    object_id: str,
    window_minutes: int,
) -> float:
    _assert_ops_admin(actor)

    feature = db.scalar(select(FeatureDefinition).where(FeatureDefinition.code == feature_code))
    if feature is None:
        raise NotFoundException("Feature definition not found")

    threshold = utcnow() - timedelta(minutes=window_minutes)
    rows = db.scalars(
        select(FeatureValue).where(
            FeatureValue.feature_definition_id == feature.id,
            FeatureValue.object_type == object_type,
            FeatureValue.object_id == object_id,
            FeatureValue.window_end >= threshold,
        )
    ).all()

    nums = [float(x.value_numeric) for x in rows if x.value_numeric is not None]
    if not nums:
        return 0.0
    return sum(nums) / len(nums)


def frequency_per_minute(
    db: Session,
    actor: User,
    feature_code: str,
    object_type: str,
    object_id: str,
    minutes: int,
) -> float:
    _assert_ops_admin(actor)

    feature = db.scalar(select(FeatureDefinition).where(FeatureDefinition.code == feature_code))
    if feature is None:
        raise NotFoundException("Feature definition not found")

    threshold = utcnow() - timedelta(minutes=minutes)
    count = len(
        db.scalars(
            select(FeatureValue).where(
                FeatureValue.feature_definition_id == feature.id,
                FeatureValue.object_type == object_type,
                FeatureValue.object_id == object_id,
                FeatureValue.created_at >= threshold,
            )
        ).all()
    )
    return 0.0 if minutes <= 0 else count / minutes


def correlation_proxy(
    db: Session,
    actor: User,
    left_feature_code: str,
    right_feature_code: str,
    object_type: str,
    object_id: str,
) -> float:
    _assert_ops_admin(actor)

    left = db.scalar(select(FeatureDefinition).where(FeatureDefinition.code == left_feature_code))
    right = db.scalar(select(FeatureDefinition).where(FeatureDefinition.code == right_feature_code))
    if left is None or right is None:
        raise NotFoundException("Feature definition not found")

    left_rows = db.scalars(
        select(FeatureValue).where(
            FeatureValue.feature_definition_id == left.id,
            FeatureValue.object_type == object_type,
            FeatureValue.object_id == object_id,
        )
    ).all()
    right_rows = db.scalars(
        select(FeatureValue).where(
            FeatureValue.feature_definition_id == right.id,
            FeatureValue.object_type == object_type,
            FeatureValue.object_id == object_id,
        )
    ).all()

    left_mean = sum(float(x.value_numeric) for x in left_rows if x.value_numeric is not None) / max(
        1, len([x for x in left_rows if x.value_numeric is not None])
    )
    right_mean = sum(float(x.value_numeric) for x in right_rows if x.value_numeric is not None) / max(
        1, len([x for x in right_rows if x.value_numeric is not None])
    )

    denom = max(abs(left_mean), abs(right_mean), 1e-9)
    return 1.0 - abs(left_mean - right_mean) / denom


def verify_feature_consistency(
    db: Session,
    actor: User,
    feature_code: str,
    object_type: str,
    object_id: str,
) -> ConsistencyCheckResponse:
    _assert_ops_admin(actor)

    feature = db.scalar(select(FeatureDefinition).where(FeatureDefinition.code == feature_code))
    if feature is None:
        raise NotFoundException("Feature definition not found")

    rows = db.scalars(
        select(FeatureValue).where(
            FeatureValue.feature_definition_id == feature.id,
            FeatureValue.object_type == object_type,
            FeatureValue.object_id == object_id,
        )
    ).all()

    if not rows:
        return ConsistencyCheckResponse(
            feature_code=feature_code,
            object_type=object_type,
            object_id=object_id,
            is_consistent=True,
            details="No values to compare",
        )

    latest = sorted(rows, key=lambda x: x.created_at, reverse=True)[0]
    expected_layer = _storage_layer(latest.expires_at)
    ok = latest.storage_layer == expected_layer

    return ConsistencyCheckResponse(
        feature_code=feature_code,
        object_type=object_type,
        object_id=object_id,
        is_consistent=ok,
        details="Layer consistent with TTL" if ok else "Layer mismatch with TTL",
    )


def build_daily_analytics(db: Session, actor: User, payload: DailyAnalyticsBuildRequest) -> DailyAnalyticsResponse:
    _assert_ops_admin(actor)

    if payload.transaction_volume == 0:
        conversion_rate = 0.0
        dispute_rate = 0.0
    else:
        conversion_rate = payload.successful_transactions / payload.transaction_volume
        dispute_rate = payload.dispute_count / payload.transaction_volume

    with transactional_session(db):
        metric = DailyOperationMetric(
            metric_day=payload.metric_day,
            transaction_volume=payload.transaction_volume,
            conversion_rate=conversion_rate,
            activity_count=payload.activity_count,
            dispute_rate=dispute_rate,
        )
        db.add(metric)
        db.flush()

    return DailyAnalyticsResponse(
        metric_day=metric.metric_day,
        transaction_volume=metric.transaction_volume,
        conversion_rate=float(metric.conversion_rate),
        activity_count=metric.activity_count,
        dispute_rate=float(metric.dispute_rate),
    )


def export_daily_analytics_csv(db: Session, actor: User) -> str:
    _assert_ops_admin(actor)

    rows = db.scalars(select(DailyOperationMetric).order_by(DailyOperationMetric.metric_day.asc())).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["metric_day", "transaction_volume", "conversion_rate", "activity_count", "dispute_rate"])

    for r in rows:
        writer.writerow(
            [
                r.metric_day.isoformat(),
                r.transaction_volume,
                float(r.conversion_rate),
                r.activity_count,
                float(r.dispute_rate),
            ]
        )

    return buffer.getvalue()


def create_operation_config(db: Session, actor: User, payload: OperationConfigCreateRequest) -> OperationConfigResponse:
    _assert_ops_admin(actor)

    latest = db.scalar(
        select(OperationConfiguration)
        .where(OperationConfiguration.config_key == payload.config_key)
        .order_by(OperationConfiguration.version.desc())
    )

    with transactional_session(db):
        if latest is not None:
            latest.is_active = False

        entity = OperationConfiguration(
            config_key=payload.config_key,
            config_value=payload.config_value,
            rollout_percent=payload.rollout_percent,
            version=1 if latest is None else latest.version + 1,
            previous_config_id=latest.id if latest else None,
            is_active=True,
            is_rolled_back=False,
            changed_by_user_id=actor.id,
        )
        db.add(entity)
        db.flush()

        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="operation_config.create",
            entity_type="operation_configuration",
            entity_id=str(entity.id),
            details={
                "config_key": entity.config_key,
                "rollout_percent": entity.rollout_percent,
                "version": entity.version,
            },
        )

    return _config_to_response(entity)


def gradual_rollout(db: Session, actor: User, config_id: int, rollout_percent: int) -> OperationConfigResponse:
    _assert_ops_admin(actor)

    if rollout_percent < 0 or rollout_percent > 100:
        raise ValidationException("rollout_percent must be between 0 and 100")

    entity = db.get(OperationConfiguration, config_id)
    if entity is None:
        raise NotFoundException("Operation configuration not found")

    with transactional_session(db):
        entity.rollout_percent = rollout_percent
        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="operation_config.rollout",
            entity_type="operation_configuration",
            entity_id=str(entity.id),
            details={"rollout_percent": rollout_percent},
        )

    return _config_to_response(entity)


def rollback_operation_config(db: Session, actor: User, config_key: str) -> OperationConfigResponse:
    _assert_ops_admin(actor)

    current = db.scalar(
        select(OperationConfiguration)
        .where(OperationConfiguration.config_key == config_key, OperationConfiguration.is_active.is_(True))
        .order_by(OperationConfiguration.version.desc())
    )
    if current is None:
        raise NotFoundException("Active operation configuration not found")
    if current.previous_config_id is None:
        raise ValidationException("No previous configuration available for rollback")

    previous = db.get(OperationConfiguration, current.previous_config_id)
    if previous is None:
        raise NotFoundException("Previous configuration not found")

    with transactional_session(db):
        current.is_active = False
        current.is_rolled_back = True
        previous.is_active = True

        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="operation_config.rollback",
            entity_type="operation_configuration",
            entity_id=str(current.id),
            details={"rolled_back_to": previous.id, "config_key": config_key},
        )

    return _config_to_response(previous)
