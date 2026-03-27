from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.schemas.payment import PaymentSettleRequest
from app.security.dependencies import get_current_active_user, require_permission
from app.services.payment_service import list_payments_by_order, settle_order

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "/settle",
    response_model=ApiResponse,
    summary="Settle Order Payment",
    description=(
        "Offline accounting settlement endpoint. Supports cash/bank-card/stored-value split payment "
        "with strict overpayment prevention and order status transition control."
    ),
    dependencies=[Depends(require_permission("payment:settle"))],
    responses={
        409: {"model": ApiErrorResponse, "description": "Duplicate/already-settled order"},
        422: {"model": ApiErrorResponse, "description": "Validation error"},
    },
)
def settle_order_payment_endpoint(
    payload: PaymentSettleRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = settle_order(db, actor=user, payload=payload)
    return ApiResponse(message="Order settlement recorded", data=result.model_dump())


@router.get(
    "/orders/{order_id}",
    response_model=ApiResponse,
    summary="List Order Payments",
    description="Returns payment records linked to an order for reconciliation.",
    dependencies=[Depends(require_permission("payment:read"))],
)
def list_order_payments_endpoint(
    order_id: int,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    records = list_payments_by_order(db, order_id=order_id)
    return ApiResponse(
        message="Order payments listed",
        data=[
            {
                "id": r.id,
                "order_id": r.order_id,
                "cashier_user_id": r.cashier_user_id,
                "method": r.method,
                "amount": str(r.amount),
                "status": r.status,
                "created_at": r.created_at.isoformat(),
            }
            for r in records
        ],
    )
