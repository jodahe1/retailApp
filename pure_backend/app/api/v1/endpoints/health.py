from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiErrorResponse, ApiResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    response_model=ApiResponse,
    summary="Health Check",
    description="Checks API and database connectivity for local/offline deployment readiness.",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Service is healthy",
                        "data": {"status": "up"},
                        "meta": None,
                    }
                }
            },
        },
        500: {
            "model": ApiErrorResponse,
            "description": "Internal error",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_code": "INTERNAL_ERROR",
                        "message": "An internal error occurred",
                        "details": None,
                    }
                }
            },
        },
    },
)
def health_check(db: Session = Depends(get_db)) -> ApiResponse:
    db.execute(text("SELECT 1"))
    return ApiResponse(message="Service is healthy", data={"status": "up"})
