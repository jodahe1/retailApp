from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ActiveSoftDeleteMixin, Base, TimestampMixin


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    REJECTED = "rejected"
    DEACTIVATED = "deactivated"


class Project(Base, TimestampMixin, ActiveSoftDeleteMixin):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_applicant_status", "applicant_user_id", "status"),
        Index("ix_projects_assigned_reviewer", "assigned_reviewer_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    applicant_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    assigned_reviewer_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    contact_phone_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(24), nullable=False, default=ProjectStatus.DRAFT)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProjectVersion(Base, TimestampMixin):
    __tablename__ = "project_versions"
    __table_args__ = (
        UniqueConstraint("project_id", "version_no", name="uq_project_versions_project_version"),
        Index("ix_project_versions_project_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)

    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    diff_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    submitted_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
