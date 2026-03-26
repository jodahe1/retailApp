from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=ApiResponse)
def health_check(db: Session = Depends(get_db)) -> ApiResponse:
    db.execute(text("SELECT 1"))
    return ApiResponse(message="Service is healthy", data={"status": "up"})
