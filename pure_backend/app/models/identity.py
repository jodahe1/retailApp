from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import ActiveSoftDeleteMixin, Base, TimestampMixin


class User(Base, TimestampMixin, ActiveSoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    id_number_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_info_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary="user_roles",
        back_populates="users",
    )


class Role(Base, TimestampMixin, ActiveSoftDeleteMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list[User]] = relationship(
        "User",
        secondary="user_roles",
        back_populates="roles",
    )
    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
    )


class Permission(Base, TimestampMixin, ActiveSoftDeleteMixin):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
    )


class UserRole(Base, TimestampMixin):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_id_role_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)


class RolePermission(Base, TimestampMixin):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_id_permission_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )


class SessionToken(Base, TimestampMixin):
    __tablename__ = "session_tokens"
    __table_args__ = (
        Index("ix_session_tokens_user_id_revoked", "user_id", "is_revoked"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    refresh_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SensitiveAccessLog(Base, TimestampMixin):
    __tablename__ = "sensitive_access_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    target_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ImmutableAuditLog(Base):
    __tablename__ = "immutable_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)


def _block_audit_mutation(*_: object, **__: object) -> None:
    raise ValueError("ImmutableAuditLog is append-only; update/delete is not allowed")


event.listen(ImmutableAuditLog, "before_update", _block_audit_mutation)
event.listen(ImmutableAuditLog, "before_delete", _block_audit_mutation)

Index("ix_users_username_unique", User.username, unique=True)
