from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PaymentLineRequest(BaseModel):
    method: str = Field(examples=["cash"])
    amount: Decimal = Field(gt=0, examples=[10.00])
    offline_approval_code: str | None = Field(default=None, examples=["OFF-12345"])
    external_reference: str | None = Field(default=None, examples=["POS-BANK-001"])


class PaymentSettleRequest(BaseModel):
    order_id: int = Field(examples=[1001])
    payments: list[PaymentLineRequest] = Field(min_length=1)


class PaymentRecordResponse(BaseModel):
    id: int
    order_id: int
    cashier_user_id: int
    method: str
    amount: Decimal
    status: str
    created_at: datetime


class PaymentSettleResponse(BaseModel):
    order_id: int
    order_status: str
    paid_amount: Decimal
    final_amount: Decimal
    remaining_amount: Decimal
    payment_records: list[PaymentRecordResponse]
