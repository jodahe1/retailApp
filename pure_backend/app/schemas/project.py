from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160, examples=["Rural Market Logistics"])
    category: str = Field(min_length=2, max_length=80, examples=["retail-tech"])
    description: str = Field(min_length=10, max_length=5000, examples=["Offline-first logistics support for stores."])
    contact_phone: str | None = Field(default=None, examples=["+251900123456"])
    assigned_reviewer_user_id: int | None = Field(default=None, examples=[18])


class ProjectEditRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160, examples=["Rural Market Logistics v2"])
    category: str | None = Field(default=None, min_length=2, max_length=80, examples=["retail-platform"])
    description: str | None = Field(default=None, min_length=10, max_length=5000, examples=["Updated project scope."])
    contact_phone: str | None = Field(default=None, examples=["+251900999999"])


class ProjectSubmitRequest(BaseModel):
    submission_note: str | None = Field(default=None, max_length=255, examples=["Initial submission for review"])


class ProjectRejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=255, examples=["Missing operational budget details"])


class ProjectResubmitRequest(BaseModel):
    submission_note: str | None = Field(default=None, max_length=255, examples=["Addressed budget and scope feedback"])


class ProjectDeactivateRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=255, examples=["Applicant requested closure"])


class ProjectResponse(BaseModel):
    id: int
    applicant_user_id: int
    assigned_reviewer_user_id: int | None
    name: str
    category: str
    description: str
    status: str
    current_version: int
    rejection_reason: str | None
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProjectVersionResponse(BaseModel):
    id: int
    project_id: int
    version_no: int
    snapshot_json: str
    diff_summary: str | None
    submitted_by_user_id: int
    created_at: datetime
