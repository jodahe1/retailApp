from datetime import datetime

from pydantic import BaseModel, Field


class FeatureDefinitionCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=128, examples=["daily_txn_volume"])
    name: str = Field(min_length=2, max_length=160, examples=["Daily Transaction Volume"])
    description: str | None = Field(default=None, examples=["Tracks rolling daily transaction count"])
    ttl_seconds: int = Field(gt=0, examples=[3600])
    default_mode: str = Field(default="online", examples=["online"])


class FeatureValueUpsertRequest(BaseModel):
    feature_code: str = Field(examples=["daily_txn_volume"])
    object_type: str = Field(examples=["store"])
    object_id: str = Field(examples=["S-101"])
    value_numeric: float | None = Field(default=None, examples=[123.45])
    value_text: str | None = Field(default=None, examples=["high"])
    processing_mode: str = Field(default="online", examples=["online"])
    lineage_source: str | None = Field(default=None, examples=["orders_pipeline"])
    lineage_run_id: str | None = Field(default=None, examples=["run-20260327-0001"])


class FeatureConsistencyRequest(BaseModel):
    feature_code: str = Field(examples=["daily_txn_volume"])
    object_type: str = Field(examples=["store"])
    object_id: str = Field(examples=["S-101"])


class OperationConfigCreateRequest(BaseModel):
    config_key: str = Field(min_length=2, max_length=128, examples=["risk_model_v2"])
    config_value: str = Field(min_length=2, max_length=10000, examples=['{"threshold": 0.82}'])
    rollout_percent: int = Field(ge=0, le=100, examples=[20])


class DailyAnalyticsBuildRequest(BaseModel):
    metric_day: datetime = Field(examples=["2026-03-27T00:00:00Z"])
    transaction_volume: int = Field(ge=0, examples=[500])
    successful_transactions: int = Field(ge=0, examples=[420])
    activity_count: int = Field(ge=0, examples=[120])
    dispute_count: int = Field(ge=0, examples=[8])


class FeatureDefinitionResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    ttl_seconds: int
    default_mode: str
    created_at: datetime


class FeatureValueResponse(BaseModel):
    id: int
    feature_definition_id: int
    object_type: str
    object_id: str
    value_numeric: float | None
    value_text: str | None
    processing_mode: str
    storage_layer: str
    expires_at: datetime
    lineage_source: str | None
    lineage_run_id: str | None
    created_at: datetime


class ConsistencyCheckResponse(BaseModel):
    feature_code: str
    object_type: str
    object_id: str
    is_consistent: bool
    details: str


class OperationConfigResponse(BaseModel):
    id: int
    config_key: str
    config_value: str
    rollout_percent: int
    version: int
    previous_config_id: int | None
    is_active: bool
    is_rolled_back: bool
    changed_by_user_id: int | None
    created_at: datetime


class DailyAnalyticsResponse(BaseModel):
    metric_day: datetime
    transaction_volume: int
    conversion_rate: float
    activity_count: int
    dispute_rate: float
