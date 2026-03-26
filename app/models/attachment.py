from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ActiveSoftDeleteMixin, Base, TimestampMixin


class Attachment(Base, TimestampMixin, ActiveSoftDeleteMixin):
    __tablename__ = "attachments"
    __table_args__ = (
        Index("ix_attachments_owner", "owner_user_id"),
        Index("ix_attachments_entity", "entity_type", "entity_id"),
        UniqueConstraint("fingerprint_sha256", name="uq_attachments_fingerprint_sha256"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
