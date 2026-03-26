from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import PermissionAssignmentRequest, RoleAssignmentRequest
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.security.dependencies import get_current_active_user, require_permission, require_superuser
from app.services.auth_service import assign_permission, assign_role

router = APIRouter(prefix="/admin/security", tags=["admin-security"])


@router.post(
    "/roles/assign",
    response_model=ApiResponse,
    summary="Assign Role to User",
    description="Assigns a role to a target user. Protected as admin-only and permission-gated.",
    dependencies=[Depends(require_superuser), Depends(require_permission("auth:role:assign"))],
    responses={
        200: {
            "description": "Role assigned",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Role assigned",
                        "data": None,
                        "meta": None,
                    }
                }
            },
        },
        403: {
            "model": ApiErrorResponse,
            "description": "Admin permission required",
        },
    },
)
def assign_role_endpoint(
    payload: RoleAssignmentRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    assign_role(db, actor=user, user_id=payload.user_id, role_id=payload.role_id)
    return ApiResponse(message="Role assigned")


@router.post(
    "/permissions/assign",
    response_model=ApiResponse,
    summary="Assign Permission to Role",
    description="Assigns a permission to a role. Protected as admin-only and permission-gated.",
    dependencies=[Depends(require_superuser), Depends(require_permission("auth:permission:assign"))],
    responses={
        200: {
            "description": "Permission assigned",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Permission assigned",
                        "data": None,
                        "meta": None,
                    }
                }
            },
        }
    },
)
def assign_permission_endpoint(
    payload: PermissionAssignmentRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    assign_permission(db, actor=user, role_id=payload.role_id, permission_id=payload.permission_id)
    return ApiResponse(message="Permission assigned")
