from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import ApiErrorResponse, ApiResponse
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectDeactivateRequest,
    ProjectEditRequest,
    ProjectRejectRequest,
    ProjectResubmitRequest,
    ProjectSubmitRequest,
)
from app.security.dependencies import get_current_active_user, require_any_permission, require_permission
from app.services.project_service import (
    create_project,
    deactivate_project,
    edit_project,
    get_project,
    list_project_versions,
    reject_project,
    resubmit_project,
    submit_project_for_review,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "",
    response_model=ApiResponse,
    summary="Create Project",
    description="Applicant creates a new entrepreneurship project in draft state.",
    dependencies=[Depends(require_permission("project:own"))],
    responses={
        200: {
            "description": "Project created",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Project created",
                        "data": {
                            "id": 1,
                            "applicant_user_id": 11,
                            "assigned_reviewer_user_id": 20,
                            "name": "Rural Market Logistics",
                            "category": "retail-tech",
                            "description": "Offline-first logistics support",
                            "status": "draft",
                            "current_version": 0,
                            "rejection_reason": None,
                            "reviewed_by_user_id": None,
                            "reviewed_at": None,
                            "created_at": "2026-03-26T08:00:00Z",
                            "updated_at": "2026-03-26T08:00:00Z",
                        },
                        "meta": None,
                    }
                }
            },
        },
        422: {"model": ApiErrorResponse, "description": "Validation error"},
    },
)
def create_project_endpoint(
    payload: ProjectCreateRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = create_project(db, actor=user, payload=payload)
    return ApiResponse(message="Project created", data=result.model_dump())


@router.patch(
    "/{project_id}",
    response_model=ApiResponse,
    summary="Edit Project Draft",
    description="Applicant edits own draft/rejected project before submission.",
    dependencies=[Depends(require_permission("project:own"))],
    responses={
        200: {
            "description": "Project updated",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Project updated",
                        "data": {
                            "id": 1,
                            "status": "draft",
                            "current_version": 0,
                            "description": "Updated scope and revenue plan.",
                        },
                        "meta": None,
                    }
                }
            },
        },
        403: {"model": ApiErrorResponse, "description": "Ownership/scope denied"},
        422: {"model": ApiErrorResponse, "description": "Invalid lifecycle state"},
    },
)
def edit_project_endpoint(
    project_id: int,
    payload: ProjectEditRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = edit_project(db, actor=user, project_id=project_id, payload=payload)
    return ApiResponse(message="Project updated", data=result.model_dump())


@router.post(
    "/{project_id}/submit",
    response_model=ApiResponse,
    summary="Submit Project For Review",
    description="Submits draft/rejected project and increments project version.",
    dependencies=[Depends(require_permission("project:own"))],
    responses={
        200: {
            "description": "Project submitted",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Project submitted",
                        "data": {"id": 1, "status": "submitted", "current_version": 1},
                        "meta": None,
                    }
                }
            },
        },
        403: {"model": ApiErrorResponse, "description": "Ownership denied"},
        422: {"model": ApiErrorResponse, "description": "Invalid lifecycle state"},
    },
)
def submit_project_endpoint(
    project_id: int,
    payload: ProjectSubmitRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = submit_project_for_review(db, actor=user, project_id=project_id, payload=payload)
    return ApiResponse(message="Project submitted", data=result.model_dump())


@router.post(
    "/{project_id}/reject",
    response_model=ApiResponse,
    summary="Reject Submitted Project",
    description="Reviewer/admin rejects a submitted project with reason.",
    dependencies=[Depends(require_any_permission(["project:review", "project:manage"]))],
    responses={
        200: {
            "description": "Project rejected",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Project rejected",
                        "data": {"id": 1, "status": "rejected", "rejection_reason": "Need detailed budget"},
                        "meta": None,
                    }
                }
            },
        },
        403: {"model": ApiErrorResponse, "description": "Reviewer scope denied"},
        422: {"model": ApiErrorResponse, "description": "Invalid lifecycle state"},
    },
)
def reject_project_endpoint(
    project_id: int,
    payload: ProjectRejectRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = reject_project(db, actor=user, project_id=project_id, payload=payload)
    return ApiResponse(message="Project rejected", data=result.model_dump())


@router.post(
    "/{project_id}/resubmit",
    response_model=ApiResponse,
    summary="Resubmit Rejected Project",
    description="Applicant resubmits rejected project and increments version.",
    dependencies=[Depends(require_permission("project:own"))],
    responses={
        200: {
            "description": "Project resubmitted",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Project resubmitted",
                        "data": {"id": 1, "status": "submitted", "current_version": 2},
                        "meta": None,
                    }
                }
            },
        },
        403: {"model": ApiErrorResponse, "description": "Ownership denied"},
        422: {"model": ApiErrorResponse, "description": "Invalid lifecycle state"},
    },
)
def resubmit_project_endpoint(
    project_id: int,
    payload: ProjectResubmitRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = resubmit_project(db, actor=user, project_id=project_id, payload=payload)
    return ApiResponse(message="Project resubmitted", data=result.model_dump())


@router.post(
    "/{project_id}/deactivate",
    response_model=ApiResponse,
    summary="Deactivate Project",
    description="Applicant owner or operation admin deactivates a project.",
    dependencies=[Depends(require_any_permission(["project:deactivate", "project:manage"]))],
    responses={
        200: {
            "description": "Project deactivated",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Project deactivated",
                        "data": {"id": 1, "status": "deactivated", "current_version": 2},
                        "meta": None,
                    }
                }
            },
        },
        403: {"model": ApiErrorResponse, "description": "Scope denied"},
    },
)
def deactivate_project_endpoint(
    project_id: int,
    payload: ProjectDeactivateRequest,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = deactivate_project(db, actor=user, project_id=project_id, payload=payload)
    return ApiResponse(message="Project deactivated", data=result.model_dump())


@router.get(
    "/{project_id}",
    response_model=ApiResponse,
    summary="Get Project",
    description="Returns project detail with object-level access checks.",
    dependencies=[Depends(require_any_permission(["project:read", "project:manage", "project:review", "project:own"]))],
    responses={
        200: {
            "description": "Project detail",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Project detail",
                        "data": {"id": 1, "status": "submitted", "current_version": 2},
                        "meta": None,
                    }
                }
            },
        },
        403: {"model": ApiErrorResponse, "description": "Access denied"},
        404: {"model": ApiErrorResponse, "description": "Project not found"},
    },
)
def get_project_endpoint(
    project_id: int,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    result = get_project(db, actor=user, project_id=project_id)
    return ApiResponse(message="Project detail", data=result.model_dump())


@router.get(
    "/{project_id}/versions",
    response_model=ApiResponse,
    summary="List Project Versions",
    description="Returns version history and retained diff summaries.",
    dependencies=[Depends(require_any_permission(["project:read", "project:manage", "project:review", "project:own"]))],
    responses={
        200: {
            "description": "Project versions listed",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Project versions listed",
                        "data": [
                            {
                                "id": 1,
                                "project_id": 1,
                                "version_no": 1,
                                "snapshot_json": "{...}",
                                "diff_summary": "Initial submission",
                                "submitted_by_user_id": 11,
                                "created_at": "2026-03-26T08:10:00Z",
                            },
                            {
                                "id": 2,
                                "project_id": 1,
                                "version_no": 2,
                                "snapshot_json": "{...}",
                                "diff_summary": "category: 'retail-tech' -> 'retail-platform'",
                                "submitted_by_user_id": 11,
                                "created_at": "2026-03-26T09:10:00Z",
                            },
                        ],
                        "meta": None,
                    }
                }
            },
        },
        403: {"model": ApiErrorResponse, "description": "Access denied"},
        404: {"model": ApiErrorResponse, "description": "Project not found"},
    },
)
def list_project_versions_endpoint(
    project_id: int,
    user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ApiResponse:
    versions = list_project_versions(db, actor=user, project_id=project_id)
    return ApiResponse(message="Project versions listed", data=[v.model_dump() for v in versions])
