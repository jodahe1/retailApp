from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions.base import ValidationException
from app.models.order import OrderLine, PromotionRule, PromotionType


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class PromotionResult:
    def __init__(self) -> None:
        self.order_discount_amount = Decimal("0")
        self.line_promo_discounts: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))


class PromotionEngine:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _active_rules(self) -> list[PromotionRule]:
        return (
            self.db.scalars(
                select(PromotionRule)
                .where(PromotionRule.is_active == 1)
                .order_by(PromotionRule.priority.asc(), PromotionRule.id.asc())
            ).all()
        )

    def _apply_spend_and_save(
        self,
        result: PromotionResult,
        rule: PromotionRule,
        current_subtotal: Decimal,
    ) -> None:
        if rule.threshold_amount is None or rule.discount_amount is None:
            return
        if current_subtotal >= rule.threshold_amount:
            result.order_discount_amount += rule.discount_amount

    def _apply_buy_and_get(self, result: PromotionResult, rule: PromotionRule, lines: list[OrderLine]) -> None:
        if rule.buy_quantity is None or rule.get_quantity is None or rule.applies_to_product_id is None:
            return

        for line in lines:
            if line.product_id != rule.applies_to_product_id:
                continue
            group = rule.buy_quantity + rule.get_quantity
            eligible_groups = line.quantity // group
            free_qty = eligible_groups * rule.get_quantity
            discount = Decimal(free_qty) * line.unit_price
            result.line_promo_discounts[line.id] += discount

    def _apply_tiered_pricing(self, result: PromotionResult, rule: PromotionRule, lines: list[OrderLine]) -> None:
        if (
            rule.tier_quantity is None
            or rule.tier_unit_price is None
            or rule.applies_to_product_id is None
        ):
            return

        for line in lines:
            if line.product_id != rule.applies_to_product_id:
                continue
            if line.quantity >= rule.tier_quantity:
                normal_total = line.unit_price * Decimal(line.quantity)
                tier_total = rule.tier_unit_price * Decimal(line.quantity)
                if normal_total > tier_total:
                    result.line_promo_discounts[line.id] += normal_total - tier_total

    def _validate_purchase_limit(self, rule: PromotionRule, lines: list[OrderLine]) -> None:
        if rule.purchase_limit_quantity is None or rule.applies_to_product_id is None:
            return

        qty = sum(line.quantity for line in lines if line.product_id == rule.applies_to_product_id)
        if qty > rule.purchase_limit_quantity:
            raise ValidationException(
                f"Purchase limit exceeded for product {rule.applies_to_product_id}: "
                f"limit={rule.purchase_limit_quantity}, requested={qty}"
            )

    def apply(self, lines: list[OrderLine], base_subtotal: Decimal) -> PromotionResult:
        result = PromotionResult()

        for rule in self._active_rules():
            rule_type = rule.rule_type
            if rule_type == PromotionType.SPEND_AND_SAVE:
                self._apply_spend_and_save(result, rule, base_subtotal)
            elif rule_type == PromotionType.BUY_AND_GET:
                self._apply_buy_and_get(result, rule, lines)
            elif rule_type == PromotionType.TIERED_PRICING:
                self._apply_tiered_pricing(result, rule, lines)
            elif rule_type == PromotionType.PURCHASE_LIMIT:
                self._validate_purchase_limit(rule, lines)

        result.order_discount_amount = money(result.order_discount_amount)
        for line_id in list(result.line_promo_discounts.keys()):
            result.line_promo_discounts[line_id] = money(result.line_promo_discounts[line_id])
        return result
