from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.schemas.operation import (
    DailyAnalyticsBuildRequest,
    FeatureConsistencyRequest,
    FeatureDefinitionCreateRequest,
    FeatureValueUpsertRequest,
    OperationConfigCreateRequest,
)
from app.security.dependencies import get_current_active_user, require_permission
from app.services.operation_service import (
    build_daily_analytics,
    correlation_proxy,
    create_feature_definition,
    create_operation_config,
    export_daily_analytics_csv,
    frequency_per_minute,
    gradual_rollout,
    rollback_operation_config,
    sliding_window_average,
    upsert_feature_value,
    verify_feature_consistency,
)

router = APIRouter(prefix="/operations", tags=["operations"])


@router.post(
    "/features/definitions",
    response_model=ApiResponse,
    summary="Create Feature Definition",
    description="Creates a feature definition with TTL and default online/offline processing mode.",
    dependencies=[Depends(require_permission("operations:admin"))],
)
def create_feature_definition_endpoint(
    payload: FeatureDefinitionCreateRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = create_feature_definition(db, actor=user, payload=payload)
    return ApiResponse(message="Feature definition created", data=result.model_dump())


@router.post(
    "/features/values",
    response_model=ApiResponse,
    summary="Upsert Feature Value",
    description="Writes feature value and routes to hot/cold layer based on TTL; stores lineage when provided.",
    dependencies=[Depends(require_permission("operations:admin"))],
)
def upsert_feature_value_endpoint(
    payload: FeatureValueUpsertRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = upsert_feature_value(db, actor=user, payload=payload)
    return ApiResponse(message="Feature value stored", data=result.model_dump())


@router.post(
    "/features/consistency-check",
    response_model=ApiResponse,
    summary="Verify Feature Consistency",
    description="Verifies feature storage-layer consistency against TTL expectations.",
    dependencies=[Depends(require_permission("operations:admin"))],
)
def verify_feature_consistency_endpoint(
    payload: FeatureConsistencyRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = verify_feature_consistency(
        db,
        actor=user,
        feature_code=payload.feature_code,
        object_type=payload.object_type,
        object_id=payload.object_id,
    )
    return ApiResponse(message="Consistency verification completed", data=result.model_dump())


@router.get(
    "/features/sliding-window",
    response_model=ApiResponse,
    summary="Sliding Window Average",
    description="Computes sliding-window average for numeric feature values.",
    dependencies=[Depends(require_permission("operations:admin"))],
)
def sliding_window_endpoint(
    feature_code: str,
    object_type: str,
    object_id: str,
    window_minutes: int = Query(default=60, ge=1, le=1440),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    value = sliding_window_average(db, user, feature_code, object_type, object_id, window_minutes)
    return ApiResponse(message="Sliding window calculated", data={"value": value})


@router.get(
    "/features/frequency",
    response_model=ApiResponse,
    summary="Feature Frequency",
    description="Calculates feature record frequency per minute for selected object.",
    dependencies=[Depends(require_permission("operations:admin"))],
)
def frequency_endpoint(
    feature_code: str,
    object_type: str,
    object_id: str,
    minutes: int = Query(default=60, ge=1, le=1440),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    value = frequency_per_minute(db, user, feature_code, object_type, object_id, minutes)
    return ApiResponse(message="Frequency calculated", data={"value": value})


@router.get(
    "/features/correlation",
    response_model=ApiResponse,
    summary="Feature Correlation Proxy",
    description="Computes proxy correlation score between two feature series for same object.",
    dependencies=[Depends(require_permission("operations:admin"))],
)
def correlation_endpoint(
    left_feature_code: str,
    right_feature_code: str,
    object_type: str,
    object_id: str,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    value = correlation_proxy(db, user, left_feature_code, right_feature_code, object_type, object_id)
    return ApiResponse(message="Correlation calculated", data={"value": value})


@router.post(
    "/analytics/daily",
    response_model=ApiResponse,
    summary="Build Daily Analytics",
    description="Aggregates daily operations metrics: transaction volume, conversion rate, activity, dispute rate.",
    dependencies=[Depends(require_permission("operations:admin"))],
)
def build_daily_analytics_endpoint(
    payload: DailyAnalyticsBuildRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = build_daily_analytics(db, actor=user, payload=payload)
    return ApiResponse(message="Daily analytics built", data=result.model_dump())


@router.get(
    "/analytics/export",
    response_class=PlainTextResponse,
    summary="Export Daily Analytics CSV",
    description="Exports daily analytics metrics as CSV.",
    dependencies=[Depends(require_permission("operations:admin"))],
)
def export_daily_analytics_endpoint(
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PlainTextResponse:
    csv_content = export_daily_analytics_csv(db, actor=user)
    return PlainTextResponse(content=csv_content, media_type="text/csv")


@router.post(
    "/configurations",
    response_model=ApiResponse,
    summary="Create Operation Configuration",
    description="Creates a versioned operation configuration with gradual rollout percent.",
    dependencies=[Depends(require_permission("operations:admin"))],
    responses={403: {"model": ApiErrorResponse}},
)
def create_operation_config_endpoint(
    payload: OperationConfigCreateRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = create_operation_config(db, actor=user, payload=payload)
    return ApiResponse(message="Operation configuration created", data=result.model_dump())


@router.post(
    "/configurations/{config_id}/rollout",
    response_model=ApiResponse,
    summary="Gradual Rollout",
    description="Adjusts rollout percent for a configuration revision.",
    dependencies=[Depends(require_permission("operations:admin"))],
)
def gradual_rollout_endpoint(
    config_id: int,
    rollout_percent: int = Query(..., ge=0, le=100, examples=[50]),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = gradual_rollout(db, actor=user, config_id=config_id, rollout_percent=rollout_percent)
    return ApiResponse(message="Gradual rollout updated", data=result.model_dump())


@router.post(
    "/configurations/rollback",
    response_model=ApiResponse,
    summary="One-Click Rollback",
    description="Rolls back active configuration to previous version for given config key.",
    dependencies=[Depends(require_permission("operations:admin"))],
)
def rollback_operation_config_endpoint(
    config_key: str = Query(..., examples=["risk_model_v2"]),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = rollback_operation_config(db, actor=user, config_key=config_key)
    return ApiResponse(message="Rollback completed", data=result.model_dump())
