"""add project lifecycle tables

Revision ID: a1b2c3d4e5f6
Revises: f0a1b2c3d4e5
Create Date: 2026-03-26 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("applicant_user_id", sa.Integer(), nullable=False),
        sa.Column("assigned_reviewer_user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("contact_phone_encrypted", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejection_reason", sa.String(length=255), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["applicant_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_reviewer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_applicant_status", "projects", ["applicant_user_id", "status"], unique=False)
    op.create_index("ix_projects_assigned_reviewer", "projects", ["assigned_reviewer_user_id"], unique=False)

    op.create_table(
        "project_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("diff_summary", sa.Text(), nullable=True),
        sa.Column("submitted_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "version_no", name="uq_project_versions_project_version"),
    )
    op.create_index("ix_project_versions_project_id", "project_versions", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_project_versions_project_id", table_name="project_versions")
    op.drop_table("project_versions")
    op.drop_index("ix_projects_assigned_reviewer", table_name="projects")
    op.drop_index("ix_projects_applicant_status", table_name="projects")
    op.drop_table("projects")
