from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import transactional_session
from app.exceptions.base import AuthorizationException, NotFoundException, ValidationException
from app.models.identity import User
from app.models.project import Project, ProjectStatus, ProjectVersion
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectDeactivateRequest,
    ProjectEditRequest,
    ProjectRejectRequest,
    ProjectResponse,
    ProjectResubmitRequest,
    ProjectSubmitRequest,
    ProjectVersionResponse,
)
from app.security.audit import write_audit_log
from app.security.encryption import FieldEncryption
from app.security.project_policy import ProjectPolicy, ProjectScopeContext
from app.security.tokens import utcnow

logger = logging.getLogger(__name__)


def _permission_codes(user: User) -> set[str]:
    return {perm.code for role in user.roles for perm in role.permissions}


def _context(user: User) -> ProjectScopeContext:
    return ProjectScopeContext(
        actor_user_id=user.id,
        actor_is_superuser=user.is_superuser,
        actor_permissions=_permission_codes(user),
    )


def _to_project_response(entity: Project) -> ProjectResponse:
    return ProjectResponse(
        id=entity.id,
        applicant_user_id=entity.applicant_user_id,
        assigned_reviewer_user_id=entity.assigned_reviewer_user_id,
        name=entity.name,
        category=entity.category,
        description=entity.description,
        status=entity.status,
        current_version=entity.current_version,
        rejection_reason=entity.rejection_reason,
        reviewed_by_user_id=entity.reviewed_by_user_id,
        reviewed_at=entity.reviewed_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _to_version_response(entity: ProjectVersion) -> ProjectVersionResponse:
    return ProjectVersionResponse(
        id=entity.id,
        project_id=entity.project_id,
        version_no=entity.version_no,
        snapshot_json=entity.snapshot_json,
        diff_summary=entity.diff_summary,
        submitted_by_user_id=entity.submitted_by_user_id,
        created_at=entity.created_at,
    )


def _load_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundException("Project not found")
    return project


def _assert_applicant_scope(user: User, project: Project) -> None:
    ctx = _context(user)
    if "project:manage" in ctx.actor_permissions:
        return
    if not ProjectPolicy.can_manage_own_project(ctx, project.applicant_user_id):
        raise AuthorizationException("Project access denied")


def _assert_review_scope(user: User, project: Project) -> None:
    ctx = _context(user)
    if not ProjectPolicy.can_review_project(
        ctx,
        applicant_user_id=project.applicant_user_id,
        assigned_reviewer_user_id=project.assigned_reviewer_user_id,
    ):
        raise AuthorizationException("Reviewer access denied for this project")


def _snapshot_payload(project: Project) -> dict[str, Any]:
    return {
        "name": project.name,
        "category": project.category,
        "description": project.description,
        "contact_phone_encrypted": project.contact_phone_encrypted,
        "status": project.status,
    }


def _build_diff_summary(previous: dict[str, Any] | None, current: dict[str, Any]) -> str:
    if previous is None:
        return "Initial submission"

    changes: list[str] = []
    for key in ["name", "category", "description", "contact_phone_encrypted", "status"]:
        before = previous.get(key)
        after = current.get(key)
        if before != after:
            if key == "contact_phone_encrypted":
                changes.append("contact_phone: updated")
            else:
                changes.append(f"{key}: '{before}' -> '{after}'")

    if not changes:
        return "No field changes since previous version"
    return "; ".join(changes)


def create_project(db: Session, actor: User, payload: ProjectCreateRequest) -> ProjectResponse:
    encryption = FieldEncryption()

    with transactional_session(db):
        project = Project(
            applicant_user_id=actor.id,
            assigned_reviewer_user_id=payload.assigned_reviewer_user_id,
            name=payload.name.strip(),
            category=payload.category.strip(),
            description=payload.description.strip(),
            contact_phone_encrypted=encryption.encrypt(payload.contact_phone),
            status=ProjectStatus.DRAFT,
            current_version=0,
        )
        db.add(project)
        db.flush()

        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="project.create",
            entity_type="project",
            entity_id=str(project.id),
            details={"status": project.status},
        )

    logger.info("project_created project_id=%s applicant_user_id=%s", project.id, actor.id)
    return _to_project_response(project)


def edit_project(db: Session, actor: User, project_id: int, payload: ProjectEditRequest) -> ProjectResponse:
    project = _load_project(db, project_id)
    _assert_applicant_scope(actor, project)

    if project.status not in {ProjectStatus.DRAFT, ProjectStatus.REJECTED}:
        raise ValidationException("Only draft/rejected projects can be edited")

    encryption = FieldEncryption()

    with transactional_session(db):
        if payload.name is not None:
            project.name = payload.name.strip()
        if payload.category is not None:
            project.category = payload.category.strip()
        if payload.description is not None:
            project.description = payload.description.strip()
        if payload.contact_phone is not None:
            project.contact_phone_encrypted = encryption.encrypt(payload.contact_phone)

        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="project.edit",
            entity_type="project",
            entity_id=str(project.id),
            details={"status": project.status},
        )

    logger.info("project_edited project_id=%s actor_user_id=%s", project.id, actor.id)
    return _to_project_response(project)


def _create_project_version(db: Session, project: Project, actor_user_id: int) -> ProjectVersion:
    previous = db.scalar(
        select(ProjectVersion)
        .where(ProjectVersion.project_id == project.id)
        .order_by(ProjectVersion.version_no.desc())
    )

    current_snapshot = _snapshot_payload(project)
    previous_snapshot = json.loads(previous.snapshot_json) if previous else None
    diff_summary = _build_diff_summary(previous_snapshot, current_snapshot)

    version = ProjectVersion(
        project_id=project.id,
        version_no=project.current_version + 1,
        snapshot_json=json.dumps(current_snapshot, ensure_ascii=True, sort_keys=True),
        diff_summary=diff_summary,
        submitted_by_user_id=actor_user_id,
    )
    db.add(version)
    db.flush()

    project.current_version = version.version_no
    return version


def submit_project_for_review(
    db: Session,
    actor: User,
    project_id: int,
    payload: ProjectSubmitRequest,
) -> ProjectResponse:
    project = _load_project(db, project_id)
    _assert_applicant_scope(actor, project)

    if project.status not in {ProjectStatus.DRAFT, ProjectStatus.REJECTED}:
        raise ValidationException("Only draft/rejected projects can be submitted")

    with transactional_session(db):
        version = _create_project_version(db, project, actor.id)
        project.status = ProjectStatus.SUBMITTED
        project.rejection_reason = None
        project.reviewed_by_user_id = None
        project.reviewed_at = None

        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="project.submit",
            entity_type="project",
            entity_id=str(project.id),
            details={
                "version_no": version.version_no,
                "submission_note": payload.submission_note,
            },
        )

    logger.info("project_submitted project_id=%s version=%s", project.id, project.current_version)
    return _to_project_response(project)


def reject_project(db: Session, actor: User, project_id: int, payload: ProjectRejectRequest) -> ProjectResponse:
    project = _load_project(db, project_id)
    _assert_review_scope(actor, project)

    if project.status != ProjectStatus.SUBMITTED:
        raise ValidationException("Only submitted projects can be rejected")

    with transactional_session(db):
        project.status = ProjectStatus.REJECTED
        project.rejection_reason = payload.reason.strip()
        project.reviewed_by_user_id = actor.id
        project.reviewed_at = utcnow()

        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="project.reject",
            entity_type="project",
            entity_id=str(project.id),
            details={"reason": project.rejection_reason},
        )

    logger.info("project_rejected project_id=%s reviewer_user_id=%s", project.id, actor.id)
    return _to_project_response(project)


def resubmit_project(
    db: Session,
    actor: User,
    project_id: int,
    payload: ProjectResubmitRequest,
) -> ProjectResponse:
    project = _load_project(db, project_id)
    _assert_applicant_scope(actor, project)

    if project.status != ProjectStatus.REJECTED:
        raise ValidationException("Only rejected projects can be resubmitted")

    with transactional_session(db):
        version = _create_project_version(db, project, actor.id)
        project.status = ProjectStatus.SUBMITTED
        project.rejection_reason = None
        project.reviewed_by_user_id = None
        project.reviewed_at = None

        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="project.resubmit",
            entity_type="project",
            entity_id=str(project.id),
            details={
                "version_no": version.version_no,
                "submission_note": payload.submission_note,
            },
        )

    logger.info("project_resubmitted project_id=%s version=%s", project.id, project.current_version)
    return _to_project_response(project)


def deactivate_project(
    db: Session,
    actor: User,
    project_id: int,
    payload: ProjectDeactivateRequest,
) -> ProjectResponse:
    project = _load_project(db, project_id)

    ctx = _context(actor)
    if "project:manage" not in ctx.actor_permissions:
        _assert_applicant_scope(actor, project)

    if project.status == ProjectStatus.DEACTIVATED:
        return _to_project_response(project)

    with transactional_session(db):
        project.status = ProjectStatus.DEACTIVATED
        project.is_active = False

        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="project.deactivate",
            entity_type="project",
            entity_id=str(project.id),
            details={"reason": payload.reason.strip()},
        )

    logger.info("project_deactivated project_id=%s actor_user_id=%s", project.id, actor.id)
    return _to_project_response(project)


def get_project(db: Session, actor: User, project_id: int) -> ProjectResponse:
    project = _load_project(db, project_id)

    ctx = _context(actor)
    if "project:manage" in ctx.actor_permissions:
        return _to_project_response(project)

    if ProjectPolicy.can_manage_own_project(ctx, project.applicant_user_id):
        return _to_project_response(project)

    if ProjectPolicy.can_review_project(
        ctx,
        applicant_user_id=project.applicant_user_id,
        assigned_reviewer_user_id=project.assigned_reviewer_user_id,
    ):
        return _to_project_response(project)

    raise AuthorizationException("Project access denied")


def list_project_versions(db: Session, actor: User, project_id: int) -> list[ProjectVersionResponse]:
    _ = get_project(db, actor, project_id)

    versions = db.scalars(
        select(ProjectVersion)
        .where(ProjectVersion.project_id == project_id)
        .order_by(ProjectVersion.version_no.asc())
    ).all()
    return [_to_version_response(v) for v in versions]
