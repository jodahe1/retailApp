import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db, transactional_session
from app.exceptions.base import ConflictException, NotFoundException
from app.models.identity import Permission, Role, User
from app.schemas.auth import PermissionAssignmentRequest, RoleAssignmentRequest
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.security.dependencies import (
    get_current_active_user,
    require_permission,
    require_superuser,
)
from app.services.auth_service import assign_permission, assign_role, reveal_sensitive_contact

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


class PermissionCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128, examples=["project:review"])
    description: str | None = Field(default=None, examples=["Allows project review operations"])


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64, examples=["store_manager"])
    description: str | None = Field(default=None, examples=["Store manager role"])


class RolePermissionsRequest(BaseModel):
    permission_ids: list[int] = Field(min_length=1, examples=[[1, 2, 3]])


class UserRolesRequest(BaseModel):
    role_ids: list[int] = Field(min_length=1, examples=[[1, 2]])


@router.post(
    "/permissions",
    response_model=ApiResponse,
    summary="Create Permission",
    description="Creates a permission code for route-level authorization mapping.",
    dependencies=[Depends(require_superuser), Depends(require_permission("auth:permission:assign"))],
    responses={
        200: {
            "description": "Permission created",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Permission created",
                        "data": {"id": 12, "code": "project:review"},
                        "meta": None,
                    }
                }
            },
        },
        409: {"model": ApiErrorResponse, "description": "Permission code already exists"},
    },
)
def create_permission_endpoint(
    payload: PermissionCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    entity = Permission(code=payload.code.strip(), description=payload.description)

    try:
        with transactional_session(db):
            db.add(entity)
            db.flush()
    except IntegrityError as exc:
        raise ConflictException("Permission code already exists") from exc

    return ApiResponse(message="Permission created", data={"id": entity.id, "code": entity.code})


@router.post(
    "/roles",
    response_model=ApiResponse,
    summary="Create Role",
    description="Creates a role used for permission aggregation.",
    dependencies=[Depends(require_superuser), Depends(require_permission("auth:role:assign"))],
    responses={
        200: {
            "description": "Role created",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Role created",
                        "data": {"id": 8, "name": "store_manager"},
                        "meta": None,
                    }
                }
            },
        },
        409: {"model": ApiErrorResponse, "description": "Role name already exists"},
    },
)
def create_role_endpoint(
    payload: RoleCreateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse:
    entity = Role(name=payload.name.strip(), description=payload.description)

    try:
        with transactional_session(db):
            db.add(entity)
            db.flush()
    except IntegrityError as exc:
        raise ConflictException("Role name already exists") from exc

    return ApiResponse(message="Role created", data={"id": entity.id, "name": entity.name})


@router.post(
    "/roles/{role_id}/permissions",
    response_model=ApiResponse,
    summary="Assign Permissions to Role",
    dependencies=[Depends(require_superuser), Depends(require_permission("auth:permission:assign"))],
    responses={
        404: {"model": ApiErrorResponse, "description": "Role not found"},
    },
)
def assign_permissions_to_role_endpoint(
    role_id: int,
    payload: RolePermissionsRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    role = db.get(Role, role_id)
    if role is None:
        raise NotFoundException("Role not found")

    assigned = 0
    for permission_id in payload.permission_ids:
        assign_permission(db, actor=user, role_id=role_id, permission_id=permission_id)
        assigned += 1

    logger.info("role_permissions_assigned actor_user_id=%s role_id=%s assigned=%s", user.id, role_id, assigned)
    return ApiResponse(message="Permissions assigned to role", data={"assigned": assigned})


@router.post(
    "/users/{user_id}/roles",
    response_model=ApiResponse,
    summary="Assign Roles to User",
    dependencies=[Depends(require_superuser), Depends(require_permission("auth:role:assign"))],
    responses={
        404: {"model": ApiErrorResponse, "description": "User not found"},
    },
)
def assign_roles_to_user_endpoint(
    user_id: int,
    payload: UserRolesRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    target = db.get(User, user_id)
    if target is None:
        raise NotFoundException("User not found")

    assigned = 0
    for role_id in payload.role_ids:
        assign_role(db, actor=user, user_id=user_id, role_id=role_id)
        assigned += 1

    logger.info("user_roles_assigned actor_user_id=%s target_user_id=%s assigned=%s", user.id, user_id, assigned)
    return ApiResponse(message="Roles assigned to user", data={"assigned": assigned})


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


@router.get(
    "/security/users/{target_user_id}/sensitive-contact",
    response_model=ApiResponse,
    summary="Read Sensitive Contact",
    description="Reads encrypted contact info for a target user and writes sensitive access logs.",
    dependencies=[Depends(require_superuser), Depends(require_permission("auth:sensitive:read"))],
    responses={
        200: {
            "description": "Sensitive contact revealed",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Sensitive contact read",
                        "data": {"target_user_id": 10, "contact_info": "+251900000000"},
                        "meta": None,
                    }
                }
            },
        },
        404: {"model": ApiErrorResponse, "description": "User not found"},
    },
)
def read_sensitive_contact_endpoint(
    target_user_id: int,
    reason: str = "compliance_verification",
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    contact = reveal_sensitive_contact(
        db,
        actor=user,
        target_user_id=target_user_id,
        reason=reason,
    )
    return ApiResponse(
        message="Sensitive contact read",
        data={"target_user_id": target_user_id, "contact_info": contact},
    )
