from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import transactional_session
from app.exceptions.base import NotFoundException, SecurityException, ValidationException
from app.models.identity import User
from app.models.order import Order, OrderLine, OrderStatus, PromotionRule
from app.schemas.order import OrderCreateRequest, OrderLineResponse, OrderResponse, PromotionRuleCreateRequest
from app.security.audit import write_audit_log
from app.security.tokens import utcnow
from app.services.promotion_engine import PromotionEngine, money
from app.services.product_service import find_product_by_query

logger = logging.getLogger(__name__)

ORDER_EXPIRY_MINUTES = 30


def _to_order_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        order_no=order.order_no,
        cashier_user_id=order.cashier_user_id,
        status=order.status,
        subtotal_amount=order.subtotal_amount,
        item_discount_total=order.item_discount_total,
        order_discount_total=order.order_discount_total,
        promotion_discount_total=order.promotion_discount_total,
        final_amount=order.final_amount,
        paid_amount=order.paid_amount,
        created_at=order.created_at,
        settled_at=order.settled_at,
        voided_at=order.voided_at,
        void_reason=order.void_reason,
        lines=[
            OrderLineResponse(
                id=l.id,
                product_id=l.product_id,
                product_name_snapshot=l.product_name_snapshot,
                product_barcode_snapshot=l.product_barcode_snapshot,
                quantity=l.quantity,
                unit_price=l.unit_price,
                line_subtotal=l.line_subtotal,
                item_discount_amount=l.item_discount_amount,
                promotion_discount_amount=l.promotion_discount_amount,
                final_line_amount=l.final_line_amount,
            )
            for l in order.lines
        ],
    )


def _calculate_order_no() -> str:
    return f"ORD-{uuid4().hex[:12].upper()}"


def create_order(db: Session, actor: User, payload: OrderCreateRequest) -> OrderResponse:
    if not payload.lines:
        raise ValidationException("Order must contain at least one line")

    with transactional_session(db):
        order = Order(
            order_no=_calculate_order_no(),
            cashier_user_id=actor.id,
            status=OrderStatus.PENDING,
            subtotal_amount=Decimal("0"),
            item_discount_total=Decimal("0"),
            order_discount_total=money(payload.order_discount_amount),
            promotion_discount_total=Decimal("0"),
            final_amount=Decimal("0"),
            paid_amount=Decimal("0"),
        )
        db.add(order)
        db.flush()

        lines: list[OrderLine] = []
        subtotal = Decimal("0")
        item_discount_total = Decimal("0")

        for input_line in payload.lines:
            product = find_product_by_query(db, query=input_line.product_query, actor=actor)
            if not product.is_available_for_sale:
                raise SecurityException(f"Product {product.id} unavailable for sale")

            line_subtotal = money(Decimal(product.unit_price) * Decimal(input_line.quantity))
            item_discount = money(input_line.item_discount_amount)
            if item_discount > line_subtotal:
                raise ValidationException("Item discount cannot exceed line subtotal")

            line = OrderLine(
                order_id=order.id,
                product_id=product.id,
                product_name_snapshot=product.name,
                product_barcode_snapshot=product.barcode,
                quantity=input_line.quantity,
                unit_price=product.unit_price,
                line_subtotal=line_subtotal,
                item_discount_amount=item_discount,
                promotion_discount_amount=Decimal("0"),
                final_line_amount=money(line_subtotal - item_discount),
            )
            db.add(line)
            db.flush()
            lines.append(line)

            subtotal += line_subtotal
            item_discount_total += item_discount

        engine = PromotionEngine(db)
        promo_result = engine.apply(lines=lines, base_subtotal=money(subtotal - item_discount_total))

        promotion_discount_total = Decimal("0")
        for line in lines:
            promo_discount = promo_result.line_promo_discounts.get(line.id, Decimal("0"))
            line.promotion_discount_amount = money(promo_discount)
            line.final_line_amount = money(line.line_subtotal - line.item_discount_amount - line.promotion_discount_amount)
            if line.final_line_amount < Decimal("0"):
                raise ValidationException("Final line amount cannot be negative")
            promotion_discount_total += line.promotion_discount_amount

        order.subtotal_amount = money(subtotal)
        order.item_discount_total = money(item_discount_total)
        order.order_discount_total = money(order.order_discount_total + promo_result.order_discount_amount)
        order.promotion_discount_total = money(promotion_discount_total)

        final_amount = money(
            order.subtotal_amount
            - order.item_discount_total
            - order.promotion_discount_total
            - order.order_discount_total
        )
        if final_amount < Decimal("0"):
            raise ValidationException("Final order amount cannot be negative")
        order.final_amount = final_amount

        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="order.create",
            entity_type="order",
            entity_id=str(order.id),
            details={"order_no": order.order_no, "final_amount": str(order.final_amount)},
        )

        logger.info(
            "order_created order_id=%s order_no=%s cashier_user_id=%s final_amount=%s",
            order.id,
            order.order_no,
            actor.id,
            order.final_amount,
        )

    loaded = db.scalar(select(Order).options(selectinload(Order.lines)).where(Order.id == order.id))
    if loaded is None:
        raise NotFoundException("Order not found after creation")
    return _to_order_response(loaded)


def get_order(db: Session, order_id: int) -> OrderResponse:
    order = db.scalar(select(Order).options(selectinload(Order.lines)).where(Order.id == order_id))
    if order is None:
        raise NotFoundException("Order not found")
    return _to_order_response(order)


def list_orders(db: Session, limit: int = 50) -> list[OrderResponse]:
    orders = db.scalars(select(Order).options(selectinload(Order.lines)).order_by(Order.id.desc()).limit(limit)).all()
    return [_to_order_response(o) for o in orders]


def create_promotion_rule(db: Session, payload: PromotionRuleCreateRequest) -> PromotionRule:
    rule = PromotionRule(
        name=payload.name,
        rule_type=payload.rule_type,
        threshold_amount=payload.threshold_amount,
        discount_amount=payload.discount_amount,
        buy_quantity=payload.buy_quantity,
        get_quantity=payload.get_quantity,
        tier_quantity=payload.tier_quantity,
        tier_unit_price=payload.tier_unit_price,
        purchase_limit_quantity=payload.purchase_limit_quantity,
        applies_to_product_id=payload.applies_to_product_id,
        is_active=True,
        priority=payload.priority,
        details=None,
    )
    with transactional_session(db):
        db.add(rule)
        db.flush()
    return rule


def expire_unpaid_orders(db: Session) -> tuple[int, int]:
    checked = 0
    voided = 0

    pending_orders = db.scalars(select(Order).where(Order.status.in_([OrderStatus.PENDING, OrderStatus.PARTIALLY_PAID]))).all()

    with transactional_session(db):
        now = utcnow()
        for order in pending_orders:
            checked += 1
            if order.created_at + timedelta(minutes=ORDER_EXPIRY_MINUTES) <= now:
                order.status = OrderStatus.VOID
                order.voided_at = now
                order.void_reason = "auto_void_unsettled_timeout"
                voided += 1
                write_audit_log(
                    db,
                    actor_user_id=None,
                    action="order.auto_void",
                    entity_type="order",
                    entity_id=str(order.id),
                    details={"order_no": order.order_no},
                )

    if voided:
        logger.info("order_auto_void_run checked=%s voided=%s", checked, voided)
    return checked, voided
