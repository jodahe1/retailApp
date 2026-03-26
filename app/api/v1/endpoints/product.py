from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.schemas.product import (
    AddToCartRequest,
    ProductCreateRequest,
    ProductQuickMatchRequest,
    ProductStatusUpdateRequest,
)
from app.security.dependencies import get_current_active_user, require_permission
from app.services.product_service import (
    build_precheckout_item,
    create_product,
    quick_match_products,
    retrieve_product,
    update_product_status,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.post(
    "",
    response_model=ApiResponse,
    summary="Create Product",
    description="Creates a POS-retrievable product record with barcode/internal/pinyin keys.",
    dependencies=[Depends(require_permission("product:manage"))],
    responses={
        200: {
            "description": "Product created",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Product created",
                        "data": {
                            "product_id": 10,
                            "barcode": "6901111111111",
                            "internal_code": "SKU-COLA-500",
                        },
                        "meta": None,
                    }
                }
            },
        }
    },
)
def create_product_endpoint(
    payload: ProductCreateRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    product = create_product(db, payload=payload, actor=user)
    return ApiResponse(
        message="Product created",
        data={"product_id": product.id, "barcode": product.barcode, "internal_code": product.internal_code},
    )


@router.get(
    "/retrieve",
    response_model=ApiResponse,
    summary="Retrieve Product",
    description="Retrieves active product by exact barcode, internal code, or pinyin key.",
    dependencies=[Depends(require_permission("product:retrieve"))],
    responses={
        200: {
            "description": "Product retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Product retrieved",
                        "data": {
                            "id": 10,
                            "name": "Cola 500ml",
                            "name_pinyin": "kele",
                            "barcode": "6901111111111",
                            "internal_code": "SKU-COLA-500",
                            "unit_price": 4.50,
                            "is_active": True,
                            "is_available_for_sale": True,
                            "is_pos_visible": True,
                        },
                        "meta": None,
                    }
                }
            },
        },
        404: {"model": ApiErrorResponse, "description": "Product not found"},
        423: {"model": ApiErrorResponse, "description": "Inactive/unavailable product"},
    },
)
def retrieve_product_endpoint(
    query: str = Query(..., min_length=1, examples=["6901234567890"]),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = retrieve_product(db, query=query, actor=user)
    return ApiResponse(message="Product retrieved", data=result.model_dump())


@router.post(
    "/quick-match",
    response_model=ApiResponse,
    summary="Quick Match Products",
    description="Cashier quick match for barcode/internal code exact match or pinyin partial match.",
    dependencies=[Depends(require_permission("product:retrieve"))],
    responses={
        200: {
            "description": "Quick match completed",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Quick match completed",
                        "data": [
                            {
                                "id": 10,
                                "name": "Cola 500ml",
                                "barcode": "6901111111111",
                                "internal_code": "SKU-COLA-500",
                                "unit_price": 4.50,
                            }
                        ],
                        "meta": None,
                    }
                }
            },
        }
    },
)
def quick_match_products_endpoint(
    payload: ProductQuickMatchRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    matches = quick_match_products(db, query=payload.query, limit=payload.limit)
    return ApiResponse(message="Quick match completed", data=[m.model_dump() for m in matches])


@router.post(
    "/precheckout/items",
    response_model=ApiResponse,
    summary="Build Pre-Checkout Item",
    description="Builds a validated pre-checkout line item from scanned product and quantity.",
    dependencies=[Depends(require_permission("checkout:item:add"))],
    responses={
        200: {
            "description": "Pre-checkout item built",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Pre-checkout item built",
                        "data": {
                            "product_id": 10,
                            "barcode": "6901111111111",
                            "internal_code": "SKU-COLA-500",
                            "name": "Cola 500ml",
                            "quantity": 2,
                            "unit_price": 4.50,
                            "line_total": 9.00,
                        },
                        "meta": None,
                    }
                }
            },
        },
        423: {"model": ApiErrorResponse, "description": "Inactive/unavailable product"},
    },
)
def build_precheckout_item_endpoint(
    payload: AddToCartRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    item = build_precheckout_item(db, actor=user, payload=payload)
    return ApiResponse(message="Pre-checkout item built", data=item.model_dump())


@router.patch(
    "/{product_id}/status",
    response_model=ApiResponse,
    summary="Update Product Status",
    description="Updates active/availability/visibility flags for checkout control.",
    dependencies=[Depends(require_permission("product:manage"))],
)
def update_product_status_endpoint(
    product_id: int,
    payload: ProductStatusUpdateRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    updated = update_product_status(db, product_id=product_id, payload=payload)
    return ApiResponse(message="Product status updated", data=updated.model_dump())
