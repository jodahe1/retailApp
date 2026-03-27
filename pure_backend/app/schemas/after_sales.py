from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ReturnRequest(BaseModel):
    original_order_id: int = Field(examples=[1001])
    refund_amount: Decimal = Field(gt=0, examples=[10.00])
    reason: str | None = Field(default=None, examples=["Damaged product"])


class ExchangeRequest(BaseModel):
    original_order_id: int = Field(examples=[1001])
    note: str | None = Field(default=None, examples=["Exchange to another size"])


class ReverseSettlementRequest(BaseModel):
    original_order_id: int = Field(examples=[1001])
    refund_amount: Decimal = Field(gt=0, examples=[10.00])
    idempotency_key: str = Field(min_length=8, max_length=128, examples=["refund-1001-001"])
    reason: str | None = Field(default=None, examples=["Customer requested refund"])


class AfterSalesResponse(BaseModel):
    id: int
    original_order_id: int
    staff_user_id: int
    after_sales_type: str
    status: str
    requested_amount: Decimal
    approved_amount: Decimal
    idempotency_key: str | None
    reason: str | None
    note: str | None
    created_at: datetime
