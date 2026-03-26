from __future__ import annotations

import base64
import hashlib

from sqlalchemy.orm import Session

from app.db.session import transactional_session
from app.exceptions.base import AuthorizationException, NotFoundException, ValidationException
from app.models.attachment import Attachment
from app.models.identity import User
from app.schemas.attachment import AttachmentCreateRequest, AttachmentResponse

ALLOWED_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_ATTACHMENT_SIZE_BYTES = 20 * 1024 * 1024


def _to_response(entity: Attachment) -> AttachmentResponse:
    return AttachmentResponse(
        id=entity.id,
        owner_user_id=entity.owner_user_id,
        entity_type=entity.entity_type,
        entity_id=entity.entity_id,
        file_name=entity.file_name,
        content_type=entity.content_type,
        file_size_bytes=entity.file_size_bytes,
        fingerprint_sha256=entity.fingerprint_sha256,
        created_at=entity.created_at,
    )


def _decode_base64_content(data: str) -> bytes:
    try:
        return base64.b64decode(data.encode("utf-8"), validate=True)
    except Exception as exc:
        raise ValidationException("Invalid base64 attachment content") from exc


def _validate_attachment_metadata(payload: AttachmentCreateRequest, raw_content: bytes) -> None:
    if payload.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationException("Unsupported file type; allowed types are PDF, JPG, PNG")

    if payload.file_size_bytes > MAX_ATTACHMENT_SIZE_BYTES:
        raise ValidationException("Attachment exceeds max size of 20MB")

    if len(raw_content) != payload.file_size_bytes:
        raise ValidationException("file_size_bytes does not match provided file content")


def _fingerprint(raw_content: bytes) -> str:
    return hashlib.sha256(raw_content).hexdigest()


def create_attachment(db: Session, actor: User, payload: AttachmentCreateRequest) -> AttachmentResponse:
    raw_content = _decode_base64_content(payload.file_content_base64)
    _validate_attachment_metadata(payload, raw_content)

    fingerprint = _fingerprint(raw_content)

    with transactional_session(db):
        attachment = Attachment(
            owner_user_id=actor.id,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            file_name=payload.file_name.strip(),
            content_type=payload.content_type,
            file_size_bytes=payload.file_size_bytes,
            fingerprint_sha256=fingerprint,
            storage_key=f"offline://attachments/{fingerprint}",
            is_active=True,
            is_deleted=False,
        )
        db.add(attachment)
        db.flush()

    return _to_response(attachment)


def get_attachment(db: Session, actor: User, attachment_id: int) -> AttachmentResponse:
    attachment = db.get(Attachment, attachment_id)
    if attachment is None or attachment.is_deleted:
        raise NotFoundException("Attachment not found")

    if attachment.owner_user_id != actor.id and not actor.is_superuser:
        raise AuthorizationException("Attachment access denied")

    return _to_response(attachment)
