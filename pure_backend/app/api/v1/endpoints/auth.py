from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserCreateRequest,
)
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.security.dependencies import get_current_active_user
from app.services.auth_service import (
    change_password,
    create_user,
    login,
    logout,
    refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/users",
    response_model=ApiResponse,
    summary="Create User",
    description="Creates a new user account with encrypted sensitive fields and hashed password.",
    responses={
        200: {
            "description": "User created",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "User created",
                        "data": {"user_id": 12, "username": "cashier01"},
                        "meta": None,
                    }
                }
            },
        },
        409: {
            "model": ApiErrorResponse,
            "description": "Username conflict",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_code": "CONFLICT",
                        "message": "Username already exists",
                        "details": None,
                    }
                }
            },
        },
    },
)
def create_user_endpoint(payload: UserCreateRequest, db: Session = Depends(get_db)) -> ApiResponse:
    user = create_user(db, payload=payload)
    return ApiResponse(message="User created", data={"user_id": user.id, "username": user.username})


@router.post(
    "/login",
    response_model=ApiResponse,
    summary="Login",
    description="Authenticates user credentials and issues access/refresh session tokens.",
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Login successful",
                        "data": {
                            "access_token": "kY9...access...token",
                            "refresh_token": "xB2...refresh...token",
                            "token_type": "bearer",
                            "expires_at": "2026-03-26T19:00:00Z",
                        },
                        "meta": None,
                    }
                }
            },
        },
        401: {
            "model": ApiErrorResponse,
            "description": "Authentication failed",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_code": "AUTHENTICATION_ERROR",
                        "message": "Invalid credentials",
                        "details": None,
                    }
                }
            },
        },
        423: {
            "model": ApiErrorResponse,
            "description": "Account locked",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error_code": "SECURITY_ERROR",
                        "message": "Account temporarily locked due to failed attempts",
                        "details": None,
                    }
                }
            },
        },
    },
)
def login_endpoint(payload: LoginRequest, db: Session = Depends(get_db)) -> ApiResponse:
    token_data: TokenResponse = login(db, payload)
    return ApiResponse(message="Login successful", data=token_data.model_dump())


@router.post(
    "/refresh",
    response_model=ApiResponse,
    summary="Refresh Session Token",
    description="Rotates session using a refresh token and returns a new access/refresh pair.",
)
def refresh_endpoint(payload: RefreshRequest, db: Session = Depends(get_db)) -> ApiResponse:
    token_data: TokenResponse = refresh_token(db, payload.refresh_token)
    return ApiResponse(message="Token refreshed", data=token_data.model_dump())


@router.post(
    "/logout",
    response_model=ApiResponse,
    summary="Logout",
    description="Revokes one or all active session tokens for the current authenticated user.",
)
def logout_endpoint(
    payload: LogoutRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    logout(db, user=user, refresh_token_value=payload.refresh_token)
    return ApiResponse(message="Logout successful")


@router.post(
    "/password/change",
    response_model=ApiResponse,
    summary="Change Password",
    description="Changes the current user password after verifying old password and policy rules.",
)
def change_password_endpoint(
    payload: ChangePasswordRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    change_password(db, user=user, payload=payload)
    return ApiResponse(message="Password changed")
