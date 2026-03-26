from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.schemas.notification import NotificationEventTriggerRequest, NotificationReadRequest, NotificationSubscribeRequest
from app.security.dependencies import get_current_active_user, require_any_permission, require_permission
from app.services.notification_service import (
    list_notifications,
    mark_notification_read,
    subscribe_event,
    trigger_notification,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post(
    "/subscriptions",
    response_model=ApiResponse,
    summary="Subscribe Notification Event",
    description="Subscribes current user to in-site or in-process event notifications.",
    dependencies=[Depends(require_permission("notification:subscribe"))],
)
def subscribe_event_endpoint(
    payload: NotificationSubscribeRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = subscribe_event(db, actor=user, payload=payload)
    return ApiResponse(message="Subscription saved", data=result.model_dump())


@router.post(
    "/trigger",
    response_model=ApiResponse,
    summary="Trigger Notification Event",
    description=(
        "Triggers in-site/in-process notification for events such as pending approvals, "
        "contract expirations, and budget alerts. Same event+object is throttled to once per 10 minutes."
    ),
    dependencies=[Depends(require_any_permission(["notification:send", "project:manage"]))],
    responses={
        200: {
            "description": "Notification triggered or throttled",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Notification processed",
                        "data": {
                            "id": 21,
                            "recipient_user_id": 12,
                            "event_type": "budget_alert",
                            "object_type": "project",
                            "object_id": "101",
                            "channel": "in_site",
                            "is_delivered": True,
                            "is_read": False,
                        },
                        "meta": None,
                    }
                }
            },
        },
        404: {"model": ApiErrorResponse, "description": "Recipient not found"},
    },
)
def trigger_notification_endpoint(
    payload: NotificationEventTriggerRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = trigger_notification(db, actor=user, payload=payload)
    return ApiResponse(message="Notification processed", data=result.model_dump() if result else {"throttled": True})


@router.get(
    "",
    response_model=ApiResponse,
    summary="List Notifications",
    description="Lists in-site notifications for current user or target user (admin only).",
    dependencies=[Depends(require_permission("notification:read"))],
)
def list_notifications_endpoint(
    target_user_id: int | None = Query(default=None, examples=[12]),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    rows = list_notifications(db, actor=user, target_user_id=target_user_id)
    return ApiResponse(message="Notifications listed", data=[x.model_dump() for x in rows])


@router.post(
    "/{notification_id}/read",
    response_model=ApiResponse,
    summary="Update Read Receipt",
    description="Marks notification read/unread and updates read receipt timestamp.",
    dependencies=[Depends(require_permission("notification:read"))],
    responses={
        403: {"model": ApiErrorResponse, "description": "Access denied"},
        404: {"model": ApiErrorResponse, "description": "Notification not found"},
    },
)
def mark_notification_read_endpoint(
    notification_id: int,
    payload: NotificationReadRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = mark_notification_read(db, actor=user, notification_id=notification_id, is_read=payload.is_read)
    return ApiResponse(message="Notification read status updated", data=result.model_dump())
