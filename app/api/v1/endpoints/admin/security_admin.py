from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.identity import Permission, Role
from app.schemas.auth import PermissionAssignmentRequest, RoleAssignmentRequest
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.security.dependencies import get_current_active_user, require_superuser
from app.services.auth_service import assign_permission, assign_role
from pydantic import BaseModel, Field

router = APIRouter(prefix="/admin", tags=["admin"])


class PermissionCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    description: str | None = None


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str | None = None


class RolePermissionsRequest(BaseModel):
    permission_ids: list[int]


class UserRolesRequest(BaseModel):
    role_ids: list[int]


@router.post(
    "/permissions",
    response_model=ApiResponse,
    summary="Create Permission",
    dependencies=[Depends(require_superuser)],
)
def create_permission_endpoint(
    payload: PermissionCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    permission = Permission(code=payload.code, description=payload.description)
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return ApiResponse(
        message="Permission created",
        data={"id": permission.id, "code": permission.code}
    )


@router.post(
    "/roles",
    response_model=ApiResponse,
    summary="Create Role",
    dependencies=[Depends(require_superuser)],
)
def create_role_endpoint(
    payload: RoleCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    role = Role(name=payload.name, description=payload.description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return ApiResponse(
        message="Role created",
        data={"id": role.id, "name": role.name}
    )


@router.post(
    "/roles/{role_id}/permissions",
    response_model=ApiResponse,
    summary="Assign Permissions to Role",
    dependencies=[Depends(require_superuser)],
)
def assign_permissions_to_role_endpoint(
    role_id: int,
    payload: RolePermissionsRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    from app.models.identity import RolePermission
    
    role = db.get(Role, role_id)
    if not role:
        return ApiResponse(success=False, message="Role not found")
    
    for perm_id in payload.permission_ids:
        existing = db.scalar(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == perm_id
            )
        )
        if not existing:
            db.add(RolePermission(role_id=role_id, permission_id=perm_id))
    
    db.commit()
    return ApiResponse(message="Permissions assigned to role")


@router.post(
    "/users/{user_id}/roles",
    response_model=ApiResponse,
    summary="Assign Roles to User",
    dependencies=[Depends(require_superuser)],
)
def assign_roles_to_user_endpoint(
    user_id: int,
    payload: UserRolesRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    from app.models.identity import User, UserRole
    
    user = db.get(User, user_id)
    if not user:
        return ApiResponse(success=False, message="User not found")
    
    for role_id in payload.role_ids:
        existing = db.scalar(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
        )
        if not existing:
            db.add(UserRole(user_id=user_id, role_id=role_id))
    
    db.commit()
    return ApiResponse(message="Roles assigned to user")


@router.post(
    "/security/roles/assign",
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
    "/security/permissions/assign",
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
