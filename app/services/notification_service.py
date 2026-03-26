from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import transactional_session
from app.exceptions.base import AuthorizationException, NotFoundException, ValidationException
from app.models.identity import User
from app.models.notification import Notification, NotificationChannel, NotificationSubscription
from app.schemas.notification import (
    NotificationEventTriggerRequest,
    NotificationResponse,
    NotificationSubscribeRequest,
    NotificationSubscriptionResponse,
)
from app.security.tokens import utcnow

logger = logging.getLogger(__name__)

THROTTLE_MINUTES = 10

EVENT_PENDING_APPROVAL = "pending_approval"
EVENT_CONTRACT_EXPIRATION = "contract_expiration"
EVENT_BUDGET_ALERT = "budget_alert"

DEFAULT_EVENTS = {
    EVENT_PENDING_APPROVAL,
    EVENT_CONTRACT_EXPIRATION,
    EVENT_BUDGET_ALERT,
}


def _to_notification_response(entity: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=entity.id,
        recipient_user_id=entity.recipient_user_id,
        event_type=entity.event_type,
        object_type=entity.object_type,
        object_id=entity.object_id,
        channel=entity.channel,
        title=entity.title,
        message=entity.message,
        is_delivered=entity.is_delivered,
        delivered_at=entity.delivered_at,
        is_read=entity.is_read,
        read_at=entity.read_at,
        created_at=entity.created_at,
    )


def _to_subscription_response(entity: NotificationSubscription) -> NotificationSubscriptionResponse:
    return NotificationSubscriptionResponse(
        id=entity.id,
        user_id=entity.user_id,
        event_type=entity.event_type,
        object_type=entity.object_type,
        channel=entity.channel,
        is_active=entity.is_active,
        created_at=entity.created_at,
    )


def subscribe_event(db: Session, actor: User, payload: NotificationSubscribeRequest) -> NotificationSubscriptionResponse:
    if payload.channel not in {NotificationChannel.IN_SITE, NotificationChannel.IN_PROCESS}:
        raise ValidationException("Unsupported notification channel")

    with transactional_session(db):
        existing = db.scalar(
            select(NotificationSubscription).where(
                NotificationSubscription.user_id == actor.id,
                NotificationSubscription.event_type == payload.event_type,
                NotificationSubscription.object_type == payload.object_type,
                NotificationSubscription.channel == payload.channel,
            )
        )
        if existing is not None:
            existing.is_active = True
            return _to_subscription_response(existing)

        entity = NotificationSubscription(
            user_id=actor.id,
            event_type=payload.event_type,
            object_type=payload.object_type,
            channel=payload.channel,
            is_active=True,
        )
        db.add(entity)
        db.flush()

    return _to_subscription_response(entity)


def _is_throttled(db: Session, recipient_user_id: int, event_type: str, object_type: str, object_id: str) -> bool:
    threshold = utcnow() - timedelta(minutes=THROTTLE_MINUTES)
    existing = db.scalar(
        select(Notification).where(
            Notification.recipient_user_id == recipient_user_id,
            Notification.event_type == event_type,
            Notification.object_type == object_type,
            Notification.object_id == object_id,
            Notification.created_at >= threshold,
        )
    )
    return existing is not None


def trigger_notification(db: Session, actor: User, payload: NotificationEventTriggerRequest) -> NotificationResponse | None:
    if payload.event_type not in DEFAULT_EVENTS:
        logger.warning("notification_unknown_event actor_user_id=%s event_type=%s", actor.id, payload.event_type)

    recipient = db.get(User, payload.recipient_user_id)
    if recipient is None:
        raise NotFoundException("Notification recipient not found")

    if _is_throttled(
        db,
        recipient_user_id=payload.recipient_user_id,
        event_type=payload.event_type,
        object_type=payload.object_type,
        object_id=payload.object_id,
    ):
        logger.info(
            "notification_throttled recipient_user_id=%s event=%s object=%s:%s",
            payload.recipient_user_id,
            payload.event_type,
            payload.object_type,
            payload.object_id,
        )
        return None

    subs = db.scalars(
        select(NotificationSubscription).where(
            NotificationSubscription.user_id == payload.recipient_user_id,
            NotificationSubscription.is_active.is_(True),
            NotificationSubscription.event_type == payload.event_type,
            or_(
                NotificationSubscription.object_type.is_(None),
                NotificationSubscription.object_type == payload.object_type,
            ),
        )
    ).all()

    channels = {NotificationChannel.IN_SITE}
    channels.update({NotificationChannel(s.channel) for s in subs if s.channel in {"in_site", "in_process"}})

    created: Notification | None = None
    with transactional_session(db):
        for channel in channels:
            entity = Notification(
                recipient_user_id=payload.recipient_user_id,
                event_type=payload.event_type,
                object_type=payload.object_type,
                object_id=payload.object_id,
                channel=channel,
                title=payload.title,
                message=payload.message,
                is_delivered=True,
                delivered_at=utcnow(),
                is_read=False,
                read_at=None,
            )
            db.add(entity)
            db.flush()
            created = entity

    return _to_notification_response(created) if created else None


def list_notifications(db: Session, actor: User, target_user_id: int | None = None) -> list[NotificationResponse]:
    user_id = target_user_id or actor.id
    if user_id != actor.id and not actor.is_superuser:
        raise AuthorizationException("Notification access denied")

    rows = db.scalars(
        select(Notification)
        .where(Notification.recipient_user_id == user_id)
        .order_by(Notification.id.desc())
    ).all()
    return [_to_notification_response(x) for x in rows]


def mark_notification_read(db: Session, actor: User, notification_id: int, is_read: bool) -> NotificationResponse:
    entity = db.get(Notification, notification_id)
    if entity is None:
        raise NotFoundException("Notification not found")

    if entity.recipient_user_id != actor.id and not actor.is_superuser:
        raise AuthorizationException("Notification access denied")

    with transactional_session(db):
        entity.is_read = is_read
        entity.read_at = utcnow() if is_read else None

    return _to_notification_response(entity)
