from datetime import datetime

from pydantic import BaseModel, Field


class AttachmentCreateRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255, examples=["proposal.pdf"])
    content_type: str = Field(examples=["application/pdf"])
    file_size_bytes: int = Field(gt=0, examples=[512000])
    file_content_base64: str = Field(min_length=1, examples=["JVBERi0xLjQKJcfs..."])
    entity_type: str | None = Field(default=None, examples=["project"])
    entity_id: str | None = Field(default=None, examples=["101"])


class AttachmentResponse(BaseModel):
    id: int
    owner_user_id: int
    entity_type: str | None
    entity_id: str | None
    file_name: str
    content_type: str
    file_size_bytes: int
    fingerprint_sha256: str
    created_at: datetime
