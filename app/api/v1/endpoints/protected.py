from fastapi import APIRouter, Depends

from app.schemas.common import ApiErrorResponse, ApiResponse
from app.security.dependencies import get_current_active_user, require_permission

router = APIRouter(prefix="/protected", tags=["protected"])


@router.get(
    "/me",
    response_model=ApiResponse,
    summary="Current User Profile",
    description="Returns basic profile details for the authenticated user.",
    responses={
        401: {
            "model": ApiErrorResponse,
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_code": "AUTHENTICATION_ERROR",
                        "message": "Authentication required",
                        "details": None,
                    }
                }
            },
        }
    },
)
def get_me(user=Depends(get_current_active_user)) -> ApiResponse:
    return ApiResponse(
        message="Authenticated",
        data={"user_id": user.id, "username": user.username, "is_superuser": user.is_superuser},
    )


@router.get(
    "/permission-test",
    response_model=ApiResponse,
    summary="Permission Guard Test",
    description="Example endpoint demonstrating route-level permission enforcement.",
    dependencies=[Depends(require_permission("system:health:read"))],
    responses={
        403: {
            "model": ApiErrorResponse,
            "description": "Permission denied",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_code": "AUTHORIZATION_ERROR",
                        "message": "Permission denied",
                        "details": None,
                    }
                }
            },
        }
    },
)
def permission_test() -> ApiResponse:
    return ApiResponse(message="Permission granted")
