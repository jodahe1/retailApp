from datetime import datetime

from pydantic import BaseModel, Field


class NotificationSubscribeRequest(BaseModel):
    event_type: str = Field(min_length=2, max_length=128, examples=["pending_approval"])
    object_type: str | None = Field(default=None, examples=["project"])
    channel: str = Field(default="in_site", examples=["in_site"])


class NotificationEventTriggerRequest(BaseModel):
    recipient_user_id: int = Field(examples=[12])
    event_type: str = Field(min_length=2, max_length=128, examples=["budget_alert"])
    object_type: str = Field(min_length=2, max_length=64, examples=["project"])
    object_id: str = Field(min_length=1, max_length=64, examples=["101"])
    title: str = Field(min_length=2, max_length=255, examples=["Budget Threshold Reached"])
    message: str = Field(min_length=2, max_length=5000, examples=["Project budget reached 90% of allocated amount"])


class NotificationReadRequest(BaseModel):
    is_read: bool = Field(default=True, examples=[True])


class NotificationResponse(BaseModel):
    id: int
    recipient_user_id: int
    event_type: str
    object_type: str
    object_id: str
    channel: str
    title: str
    message: str
    is_delivered: bool
    delivered_at: datetime | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class NotificationSubscriptionResponse(BaseModel):
    id: int
    user_id: int
    event_type: str
    object_type: str | None
    channel: str
    is_active: bool
    created_at: datetime
