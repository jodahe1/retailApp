from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import transactional_session
from app.exceptions.base import ConflictException, NotFoundException, SecurityException, ValidationException
from app.models.identity import User
from app.models.order import Order, OrderStatus
from app.models.payment import PaymentMethod, PaymentRecord, PaymentStatus
from app.schemas.payment import PaymentSettleRequest, PaymentSettleResponse
from app.security.audit import write_audit_log
from app.security.tokens import utcnow
from app.services.promotion_engine import money

logger = logging.getLogger(__name__)


NON_CASH_METHODS = {PaymentMethod.BANK_CARD, PaymentMethod.STORED_VALUE}


def _validate_method(method: str) -> PaymentMethod:
    try:
        return PaymentMethod(method)
    except ValueError as exc:
        raise ValidationException(f"Unsupported payment method: {method}") from exc


def _safe_payment_log(order_id: int, method: str, amount: Decimal) -> None:
    logger.info(
        "payment_recorded order_id=%s method=%s amount=%s",
        order_id,
        method,
        money(amount),
    )


def _remaining(order: Order) -> Decimal:
    return money(order.final_amount - order.paid_amount)


def settle_order(db: Session, actor: User, payload: PaymentSettleRequest) -> PaymentSettleResponse:
    order = db.get(Order, payload.order_id)
    if order is None:
        raise NotFoundException("Order not found")

    if order.status == OrderStatus.VOID:
        raise SecurityException("Cannot settle a void order")
    if order.status == OrderStatus.SETTLED:
        raise ConflictException("Order already settled")

    if not payload.payments:
        raise ValidationException("At least one payment line is required")

    current_remaining = _remaining(order)
    if current_remaining <= Decimal("0"):
        raise ConflictException("Order has no payable remaining amount")

    lines_total = Decimal("0")
    normalized_lines: list[tuple[PaymentMethod, Decimal, str | None, str | None]] = []

    for line in payload.payments:
        method = _validate_method(line.method)
        amount = money(line.amount)
        if amount <= Decimal("0"):
            raise ValidationException("Payment amount must be greater than 0")

        if method in NON_CASH_METHODS and (not line.offline_approval_code or len(line.offline_approval_code.strip()) < 4):
            raise ValidationException(
                f"offline_approval_code is required for method {method.value} in offline accounting mode"
            )

        normalized_lines.append((method, amount, line.offline_approval_code, line.external_reference))
        lines_total += amount

    lines_total = money(lines_total)
    if lines_total > current_remaining:
        raise ValidationException(
            f"Overpayment is not allowed: remaining={current_remaining}, attempted={lines_total}"
        )

    created_records: list[PaymentRecord] = []

    with transactional_session(db):
        for method, amount, approval, reference in normalized_lines:
            record = PaymentRecord(
                order_id=order.id,
                cashier_user_id=actor.id,
                method=method.value,
                amount=amount,
                status=PaymentStatus.COMPLETED,
                offline_approval_code=approval.strip() if approval else None,
                external_reference=reference,
            )
            db.add(record)
            db.flush()
            created_records.append(record)
            _safe_payment_log(order.id, method.value, amount)

        order.paid_amount = money(order.paid_amount + lines_total)

        if order.paid_amount == order.final_amount:
            order.status = OrderStatus.SETTLED
            order.settled_at = utcnow()
        elif order.paid_amount == Decimal("0"):
            order.status = OrderStatus.PENDING
        else:
            order.status = OrderStatus.PARTIALLY_PAID

        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="payment.settle",
            entity_type="order",
            entity_id=str(order.id),
            details={
                "order_no": order.order_no,
                "settle_amount": str(lines_total),
                "paid_amount": str(order.paid_amount),
                "order_status": order.status,
            },
        )

    return PaymentSettleResponse(
        order_id=order.id,
        order_status=order.status,
        paid_amount=money(order.paid_amount),
        final_amount=money(order.final_amount),
        remaining_amount=money(order.final_amount - order.paid_amount),
        payment_records=[
            {
                "id": r.id,
                "order_id": r.order_id,
                "cashier_user_id": r.cashier_user_id,
                "method": r.method,
                "amount": money(r.amount),
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in created_records
        ],
    )


def list_payments_by_order(db: Session, order_id: int) -> list[PaymentRecord]:
    return db.scalars(
        select(PaymentRecord)
        .where(PaymentRecord.order_id == order_id)
        .order_by(PaymentRecord.id.asc())
    ).all()
