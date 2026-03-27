from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.attachment import AttachmentCreateRequest
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.security.dependencies import get_current_active_user, require_permission
from app.services.attachment_service import create_attachment, get_attachment

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.post(
    "",
    response_model=ApiResponse,
    summary="Create Attachment Metadata",
    description="Validates attachment metadata and stores file fingerprint for integrity verification.",
    dependencies=[Depends(require_permission("attachment:manage"))],
    responses={
        200: {
            "description": "Attachment created",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Attachment created",
                        "data": {
                            "id": 1,
                            "owner_user_id": 12,
                            "file_name": "proposal.pdf",
                            "content_type": "application/pdf",
                            "file_size_bytes": 1024,
                            "fingerprint_sha256": "b1946ac92492d2347c6235b4d2611184f1e0f3a6d7e4d68ebf9b31a8f9c5ef5d",
                        },
                        "meta": None,
                    }
                }
            },
        },
        422: {"model": ApiErrorResponse, "description": "Validation error"},
    },
)
def create_attachment_endpoint(
    payload: AttachmentCreateRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = create_attachment(db, actor=user, payload=payload)
    return ApiResponse(message="Attachment created", data=result.model_dump())


@router.get(
    "/{attachment_id}",
    response_model=ApiResponse,
    summary="Get Attachment Metadata",
    description="Returns attachment metadata for authorized owner/admin.",
    dependencies=[Depends(require_permission("attachment:read"))],
    responses={
        403: {"model": ApiErrorResponse, "description": "Access denied"},
        404: {"model": ApiErrorResponse, "description": "Attachment not found"},
    },
)
def get_attachment_endpoint(
    attachment_id: int,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = get_attachment(db, actor=user, attachment_id=attachment_id)
    return ApiResponse(message="Attachment detail", data=result.model_dump())
