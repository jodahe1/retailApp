from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class OrderLineCreateRequest(BaseModel):
    product_query: str = Field(min_length=1, max_length=255, examples=["6901111111111"])
    quantity: int = Field(ge=1, le=999, examples=[2])
    item_discount_amount: Decimal = Field(default=0, ge=0, examples=[1.00])


class OrderCreateRequest(BaseModel):
    lines: list[OrderLineCreateRequest] = Field(min_length=1)
    order_discount_amount: Decimal = Field(default=0, ge=0, examples=[2.50])


class OrderLineResponse(BaseModel):
    id: int
    product_id: int
    product_name_snapshot: str
    product_barcode_snapshot: str
    quantity: int
    unit_price: Decimal
    line_subtotal: Decimal
    item_discount_amount: Decimal
    promotion_discount_amount: Decimal
    final_line_amount: Decimal


class OrderResponse(BaseModel):
    id: int
    order_no: str
    cashier_user_id: int
    status: str
    subtotal_amount: Decimal
    item_discount_total: Decimal
    order_discount_total: Decimal
    promotion_discount_total: Decimal
    final_amount: Decimal
    created_at: datetime
    settled_at: datetime | None
    voided_at: datetime | None
    void_reason: str | None
    lines: list[OrderLineResponse]


class PromotionRuleCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120, examples=["Spend 100 Save 10"])
    rule_type: str = Field(examples=["spend_and_save"])

    threshold_amount: Decimal | None = Field(default=None, ge=0, examples=[100.00])
    discount_amount: Decimal | None = Field(default=None, ge=0, examples=[10.00])

    buy_quantity: int | None = Field(default=None, ge=1, examples=[2])
    get_quantity: int | None = Field(default=None, ge=1, examples=[1])

    tier_quantity: int | None = Field(default=None, ge=1, examples=[3])
    tier_unit_price: Decimal | None = Field(default=None, ge=0, examples=[4.00])

    purchase_limit_quantity: int | None = Field(default=None, ge=1, examples=[5])

    applies_to_product_id: int | None = Field(default=None, examples=[1])
    priority: int = Field(default=100, ge=1, le=1000)


class OrderExpirationRunResponse(BaseModel):
    checked_orders: int
    voided_orders: int
