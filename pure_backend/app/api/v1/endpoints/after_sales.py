from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.after_sales import ExchangeRequest, ReturnRequest, ReverseSettlementRequest
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.security.dependencies import get_current_active_user, require_permission
from app.services.after_sales_service import create_exchange, create_return, reverse_settlement_refund

router = APIRouter(prefix="/after-sales", tags=["after-sales"])


@router.post(
    "/returns",
    response_model=ApiResponse,
    summary="Create Return",
    description="Creates after-sales return request tied to original order with 7-day and refund-ceiling validation.",
    dependencies=[Depends(require_permission("after_sales:handle"))],
    responses={
        200: {
            "description": "Return processed",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Return processed",
                        "data": {
                            "id": 1,
                            "original_order_id": 1001,
                            "staff_user_id": 12,
                            "after_sales_type": "return",
                            "status": "completed",
                            "requested_amount": 10.0,
                            "approved_amount": 10.0,
                            "idempotency_key": None,
                            "reason": "Damaged package",
                            "note": None,
                            "created_at": "2026-03-26T10:30:00Z",
                        },
                        "meta": None,
                    }
                }
            },
        },
        403: {"model": ApiErrorResponse, "description": "Permission denied"},
        404: {"model": ApiErrorResponse, "description": "Original order not found"},
        422: {"model": ApiErrorResponse, "description": "Validation error"},
    },
)
def create_return_endpoint(
    payload: ReturnRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = create_return(db, actor=user, payload=payload)
    return ApiResponse(message="Return processed", data=result.model_dump())


@router.post(
    "/exchanges",
    response_model=ApiResponse,
    summary="Create Exchange",
    description="Creates after-sales exchange record tied to original order with 7-day validation.",
    dependencies=[Depends(require_permission("after_sales:handle"))],
    responses={
        200: {
            "description": "Exchange processed",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Exchange processed",
                        "data": {
                            "id": 2,
                            "original_order_id": 1001,
                            "staff_user_id": 12,
                            "after_sales_type": "exchange",
                            "status": "completed",
                            "requested_amount": 0.0,
                            "approved_amount": 0.0,
                            "idempotency_key": None,
                            "reason": None,
                            "note": "Exchange to another size",
                            "created_at": "2026-03-26T10:35:00Z",
                        },
                        "meta": None,
                    }
                }
            },
        },
        403: {"model": ApiErrorResponse, "description": "Permission denied"},
        404: {"model": ApiErrorResponse, "description": "Original order not found"},
        422: {"model": ApiErrorResponse, "description": "Validation error"},
    },
)
def create_exchange_endpoint(
    payload: ExchangeRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = create_exchange(db, actor=user, payload=payload)
    return ApiResponse(message="Exchange processed", data=result.model_dump())


@router.post(
    "/reverse-settlements",
    response_model=ApiResponse,
    summary="Reverse Settlement Refund",
    description=(
        "Performs reverse settlement refund tied to original order. "
        "Requires idempotency key and enforces 7-day and refund ceiling constraints."
    ),
    dependencies=[Depends(require_permission("after_sales:refund"))],
    responses={
        200: {
            "description": "Reverse settlement processed",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Reverse settlement processed",
                        "data": {
                            "id": 3,
                            "original_order_id": 1001,
                            "staff_user_id": 12,
                            "after_sales_type": "refund",
                            "status": "completed",
                            "requested_amount": 6.0,
                            "approved_amount": 6.0,
                            "idempotency_key": "refund-1001-001",
                            "reason": "Customer requested refund",
                            "note": None,
                            "created_at": "2026-03-26T10:40:00Z",
                        },
                        "meta": None,
                    }
                }
            },
        },
        403: {"model": ApiErrorResponse, "description": "Permission denied"},
        404: {"model": ApiErrorResponse, "description": "Original order not found"},
        409: {"model": ApiErrorResponse, "description": "Idempotency conflict"},
        422: {"model": ApiErrorResponse, "description": "Validation error"},
    },
)
def reverse_settlement_endpoint(
    payload: ReverseSettlementRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = reverse_settlement_refund(db, actor=user, payload=payload)
    return ApiResponse(message="Reverse settlement processed", data=result.model_dump())
