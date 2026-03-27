from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import transactional_session
from app.exceptions.base import ConflictException, NotFoundException, SecurityException, ValidationException
from app.models.after_sales import AfterSalesOrder, AfterSalesStatus, AfterSalesType
from app.models.identity import User
from app.models.order import Order, OrderStatus
from app.schemas.after_sales import (
    AfterSalesResponse,
    ExchangeRequest,
    ReturnRequest,
    ReverseSettlementRequest,
)
from app.security.audit import write_audit_log
from app.security.tokens import utcnow
from app.services.promotion_engine import money

logger = logging.getLogger(__name__)

RETURN_WINDOW_DAYS = 7


def _to_response(entity: AfterSalesOrder) -> AfterSalesResponse:
    return AfterSalesResponse(
        id=entity.id,
        original_order_id=entity.original_order_id,
        staff_user_id=entity.staff_user_id,
        after_sales_type=entity.after_sales_type,
        status=entity.status,
        requested_amount=money(entity.requested_amount),
        approved_amount=money(entity.approved_amount),
        idempotency_key=entity.idempotency_key,
        reason=entity.reason,
        note=entity.note,
        created_at=entity.created_at,
    )


def _get_original_order(db: Session, order_id: int) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundException("Original order not found")
    if order.status == OrderStatus.VOID:
        raise ValidationException("Cannot process after-sales for void order")
    return order


def _validate_return_window(order: Order) -> None:
    deadline = order.created_at + timedelta(days=RETURN_WINDOW_DAYS)
    if utcnow() > deadline:
        raise ValidationException("Return window expired (7 days)")


def _total_refunded(db: Session, order_id: int) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(AfterSalesOrder.approved_amount), 0)).where(
            AfterSalesOrder.original_order_id == order_id,
            AfterSalesOrder.after_sales_type == AfterSalesType.REFUND,
            AfterSalesOrder.status == AfterSalesStatus.COMPLETED,
        )
    )
    return money(Decimal(value))


def _validate_refund_ceiling(db: Session, order: Order, refund_amount: Decimal) -> None:
    already_refunded = _total_refunded(db, order.id)
    if already_refunded + refund_amount > money(order.final_amount):
        raise ValidationException(
            f"Refund exceeds original order amount: refunded={already_refunded}, "
            f"requested={refund_amount}, order_total={money(order.final_amount)}"
        )


def _validate_idempotent_refund_request(existing: AfterSalesOrder, payload: ReverseSettlementRequest) -> None:
    if existing.original_order_id != payload.original_order_id or money(existing.requested_amount) != money(payload.refund_amount):
        logger.warning(
            "after_sales_refund_idempotency_mismatch key=%s existing_order_id=%s new_order_id=%s existing_amount=%s new_amount=%s",
            payload.idempotency_key,
            existing.original_order_id,
            payload.original_order_id,
            money(existing.requested_amount),
            money(payload.refund_amount),
        )
        raise ConflictException("Idempotency key already used with different request payload")


def create_return(db: Session, actor: User, payload: ReturnRequest) -> AfterSalesResponse:
    order = _get_original_order(db, payload.original_order_id)
    _validate_return_window(order)

    refund_amount = money(payload.refund_amount)
    _validate_refund_ceiling(db, order, refund_amount)

    with transactional_session(db):
        record = AfterSalesOrder(
            original_order_id=order.id,
            staff_user_id=actor.id,
            after_sales_type=AfterSalesType.RETURN,
            status=AfterSalesStatus.COMPLETED,
            requested_amount=refund_amount,
            approved_amount=refund_amount,
            reason=payload.reason,
        )
        db.add(record)
        db.flush()

        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="after_sales.return",
            entity_type="after_sales_order",
            entity_id=str(record.id),
            details={"original_order_id": order.id, "amount": str(refund_amount)},
        )

    logger.info("after_sales_return_created order_id=%s after_sales_id=%s", order.id, record.id)
    return _to_response(record)


def create_exchange(db: Session, actor: User, payload: ExchangeRequest) -> AfterSalesResponse:
    order = _get_original_order(db, payload.original_order_id)
    _validate_return_window(order)

    with transactional_session(db):
        record = AfterSalesOrder(
            original_order_id=order.id,
            staff_user_id=actor.id,
            after_sales_type=AfterSalesType.EXCHANGE,
            status=AfterSalesStatus.COMPLETED,
            requested_amount=Decimal("0"),
            approved_amount=Decimal("0"),
            note=payload.note,
        )
        db.add(record)
        db.flush()

        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="after_sales.exchange",
            entity_type="after_sales_order",
            entity_id=str(record.id),
            details={"original_order_id": order.id},
        )

    logger.info("after_sales_exchange_created order_id=%s after_sales_id=%s", order.id, record.id)
    return _to_response(record)


def reverse_settlement_refund(db: Session, actor: User, payload: ReverseSettlementRequest) -> AfterSalesResponse:
    order = _get_original_order(db, payload.original_order_id)
    _validate_return_window(order)

    if order.status not in [OrderStatus.PARTIALLY_PAID, OrderStatus.SETTLED]:
        raise ValidationException("Reverse settlement requires paid or partially paid order")

    refund_amount = money(payload.refund_amount)
    if refund_amount <= Decimal("0"):
        raise ValidationException("Refund amount must be greater than zero")

    if refund_amount > money(order.paid_amount):
        raise ValidationException(
            f"Refund amount exceeds paid amount: paid={money(order.paid_amount)}, requested={refund_amount}"
        )

    _validate_refund_ceiling(db, order, refund_amount)

    existing = db.scalar(
        select(AfterSalesOrder).where(
            AfterSalesOrder.idempotency_key == payload.idempotency_key,
            AfterSalesOrder.after_sales_type == AfterSalesType.REFUND,
        )
    )
    if existing is not None:
        _validate_idempotent_refund_request(existing, payload)
        logger.info(
            "after_sales_refund_idempotent_hit order_id=%s idempotency_key=%s after_sales_id=%s",
            order.id,
            payload.idempotency_key,
            existing.id,
        )
        return _to_response(existing)

    with transactional_session(db):
        record = AfterSalesOrder(
            original_order_id=order.id,
            staff_user_id=actor.id,
            after_sales_type=AfterSalesType.REFUND,
            status=AfterSalesStatus.COMPLETED,
            requested_amount=refund_amount,
            approved_amount=refund_amount,
            idempotency_key=payload.idempotency_key,
            reason=payload.reason,
        )
        db.add(record)

        try:
            db.flush()
        except IntegrityError as exc:
            conflict = db.scalar(
                select(AfterSalesOrder).where(
                    AfterSalesOrder.idempotency_key == payload.idempotency_key,
                    AfterSalesOrder.after_sales_type == AfterSalesType.REFUND,
                )
            )
            if conflict is not None:
                _validate_idempotent_refund_request(conflict, payload)
                logger.warning("after_sales_refund_duplicate_key idempotency_key=%s", payload.idempotency_key)
                return _to_response(conflict)
            raise ConflictException("Duplicate idempotency key") from exc

        order.paid_amount = money(order.paid_amount - refund_amount)
        if order.paid_amount < Decimal("0"):
            raise SecurityException("Internal payment inconsistency detected")

        if order.paid_amount == Decimal("0"):
            order.status = OrderStatus.PENDING
            order.settled_at = None
        elif order.paid_amount < money(order.final_amount):
            order.status = OrderStatus.PARTIALLY_PAID
            order.settled_at = None
        else:
            order.status = OrderStatus.SETTLED

        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="after_sales.reverse_settlement",
            entity_type="after_sales_order",
            entity_id=str(record.id),
            details={
                "original_order_id": order.id,
                "refund_amount": str(refund_amount),
                "idempotency_key": payload.idempotency_key,
                "new_paid_amount": str(order.paid_amount),
            },
        )

    logger.info(
        "after_sales_refund_completed order_id=%s after_sales_id=%s amount=%s",
        order.id,
        record.id,
        refund_amount,
    )
    return _to_response(record)
