from decimal import Decimal

from pydantic import BaseModel, Field


class ProductCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255, examples=["Orange Juice 1L"])
    name_pinyin: str = Field(min_length=1, max_length=255, examples=["chengzhi"])
    barcode: str = Field(min_length=4, max_length=64, examples=["6901234567890"])
    internal_code: str = Field(min_length=2, max_length=64, examples=["SKU-OJ-001"])
    unit_price: Decimal = Field(gt=0, examples=[6.50])
    is_available_for_sale: bool = Field(default=True, examples=[True])
    is_pos_visible: bool = Field(default=True, examples=[True])


class ProductSearchResponse(BaseModel):
    id: int
    name: str
    name_pinyin: str
    barcode: str
    internal_code: str
    unit_price: Decimal
    is_active: bool
    is_available_for_sale: bool
    is_pos_visible: bool


class ProductQuickMatchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=255, examples=["6901234567890"])
    limit: int = Field(default=10, ge=1, le=30, examples=[10])


class ProductQuickMatchItem(BaseModel):
    id: int
    name: str
    barcode: str
    internal_code: str
    unit_price: Decimal


class AddToCartRequest(BaseModel):
    query: str = Field(min_length=1, max_length=255, examples=["SKU-OJ-001"])
    quantity: int = Field(default=1, ge=1, le=999, examples=[2])


class PreCheckoutItem(BaseModel):
    product_id: int
    barcode: str
    internal_code: str
    name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class ProductStatusUpdateRequest(BaseModel):
    is_active: bool | None = Field(default=None, examples=[True])
    is_available_for_sale: bool | None = Field(default=None, examples=[True])
    is_pos_visible: bool | None = Field(default=None, examples=[True])
