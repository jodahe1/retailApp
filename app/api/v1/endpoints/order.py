from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.schemas.order import OrderCreateRequest, OrderExpirationRunResponse, PromotionRuleCreateRequest
from app.security.dependencies import get_current_active_user, require_permission
from app.services.order_service import create_order, create_promotion_rule, expire_unpaid_orders, get_order, list_orders

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "",
    response_model=ApiResponse,
    summary="Create Order",
    description="Creates order with item discounts, promotions, and final amount calculation pipeline.",
    dependencies=[Depends(require_permission("order:create"))],
    responses={
        200: {
            "description": "Order created",
            "content": {"application/json": {"example": {"success": True, "message": "Order created"}}},
        },
        422: {"model": ApiErrorResponse, "description": "Validation error"},
    },
)
def create_order_endpoint(payload: OrderCreateRequest, user=Depends(get_current_active_user), db: Session = Depends(get_db)) -> ApiResponse:
    result = create_order(db, actor=user, payload=payload)
    return ApiResponse(message="Order created", data=result.model_dump())


@router.get(
    "",
    response_model=ApiResponse,
    summary="List Orders",
    description="Returns latest orders for cashier/manager verification.",
    dependencies=[Depends(require_permission("order:read"))],
)
def list_orders_endpoint(
    limit: int = Query(default=50, ge=1, le=200),
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = list_orders(db, limit=limit)
    return ApiResponse(message="Orders listed", data=[x.model_dump() for x in result])


@router.get(
    "/{order_id}",
    response_model=ApiResponse,
    summary="Get Order Detail",
    description="Returns full order detail including lines and discount breakdown.",
    dependencies=[Depends(require_permission("order:read"))],
    responses={404: {"model": ApiErrorResponse, "description": "Order not found"}},
)
def get_order_endpoint(order_id: int, user=Depends(get_current_active_user), db: Session = Depends(get_db)) -> ApiResponse:
    result = get_order(db, order_id=order_id)
    return ApiResponse(message="Order detail", data=result.model_dump())


@router.post(
    "/promotions",
    response_model=ApiResponse,
    summary="Create Promotion Rule",
    description="Creates promotion rules for spend-save, buy-get, tiered pricing, and purchase limits.",
    dependencies=[Depends(require_permission("promotion:manage"))],
)
def create_promotion_rule_endpoint(
    payload: PromotionRuleCreateRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    rule = create_promotion_rule(db, payload=payload)
    return ApiResponse(message="Promotion rule created", data={"rule_id": rule.id, "name": rule.name})


@router.post(
    "/maintenance/expire-unpaid",
    response_model=ApiResponse,
    summary="Expire Unpaid Orders",
    description="Offline-safe maintenance endpoint to void pending orders older than 30 minutes.",
    dependencies=[Depends(require_permission("order:manage"))],
)
def expire_unpaid_orders_endpoint(user=Depends(get_current_active_user), db: Session = Depends(get_db)) -> ApiResponse:
    checked, voided = expire_unpaid_orders(db)
    payload = OrderExpirationRunResponse(checked_orders=checked, voided_orders=voided)
    return ApiResponse(message="Order expiration run completed", data=payload.model_dump())
