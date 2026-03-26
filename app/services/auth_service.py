from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.db.session import transactional_session
from app.exceptions.base import (
    AuthenticationException,
    ConflictException,
    NotFoundException,
    SecurityException,
    ValidationException,
)
from app.models.identity import Permission, Role, RolePermission, SessionToken, User, UserRole
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UserCreateRequest,
)
from app.security.access_log import record_sensitive_access
from app.security.audit import write_audit_log
from app.security.encryption import FieldEncryption
from app.security.passwords import (
    generate_token,
    hash_password,
    validate_password_policy,
    verify_password,
)
from app.security.tokens import build_access_expiry, build_refresh_expiry, hash_token, utcnow

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCK_MINUTES = 15


def create_user(db: Session, payload: UserCreateRequest, actor_user_id: int | None = None) -> User:
    validate_password_policy(payload.password)
    encryption = FieldEncryption()

    user = User(
        username=payload.username.strip(),
        password_hash=hash_password(payload.password),
        id_number_encrypted=encryption.encrypt(payload.id_number),
        contact_info_encrypted=encryption.encrypt(payload.contact_info),
    )

    try:
        with transactional_session(db):
            db.add(user)
            db.flush()
            write_audit_log(
                db,
                actor_user_id=actor_user_id,
                action="user.create",
                entity_type="user",
                entity_id=str(user.id),
                details={"username": user.username},
            )
    except IntegrityError as exc:
        raise ConflictException("Username already exists") from exc

    return user


def _load_user_for_auth(db: Session, username: str) -> User | None:
    return db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.username == username)
    )


def _lock_user_if_needed(user: User) -> None:
    if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
        user.locked_until = utcnow() + timedelta(minutes=LOCK_MINUTES)


def login(db: Session, payload: LoginRequest) -> TokenResponse:
    user = _load_user_for_auth(db, payload.username)
    if user is None or user.is_deleted or not user.is_active:
        raise AuthenticationException("Invalid credentials")

    now = utcnow()
    if user.locked_until is not None and user.locked_until > now:
        raise SecurityException("Account temporarily locked due to failed attempts")

    if not verify_password(payload.password, user.password_hash):
        with transactional_session(db):
            user.failed_login_attempts += 1
            _lock_user_if_needed(user)
            write_audit_log(
                db,
                actor_user_id=user.id,
                action="auth.login.failed",
                entity_type="user",
                entity_id=str(user.id),
                details={"failed_login_attempts": user.failed_login_attempts},
            )
        raise AuthenticationException("Invalid credentials")

    access_token = generate_token()
    refresh_token = generate_token()
    access_expiry = build_access_expiry()
    refresh_expiry = build_refresh_expiry()

    with transactional_session(db):
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        db.add(
            SessionToken(
                user_id=user.id,
                token_hash=hash_token(access_token),
                refresh_token_hash=hash_token(refresh_token),
                expires_at=access_expiry,
                refresh_expires_at=refresh_expiry,
                is_revoked=False,
            )
        )
        write_audit_log(
            db,
            actor_user_id=user.id,
            action="auth.login.success",
            entity_type="user",
            entity_id=str(user.id),
            details={},
        )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=access_expiry,
    )


def refresh_token(db: Session, refresh_token_value: str) -> TokenResponse:
    refresh_hash = hash_token(refresh_token_value)
    token_record = db.scalar(
        select(SessionToken).where(SessionToken.refresh_token_hash == refresh_hash)
    )
    if token_record is None or token_record.is_revoked or token_record.refresh_expires_at <= utcnow():
        raise AuthenticationException("Invalid refresh token")

    new_access = generate_token()
    new_refresh = generate_token()
    new_access_expiry = build_access_expiry()
    new_refresh_expiry = build_refresh_expiry()

    with transactional_session(db):
        token_record.is_revoked = True
        db.add(
            SessionToken(
                user_id=token_record.user_id,
                token_hash=hash_token(new_access),
                refresh_token_hash=hash_token(new_refresh),
                expires_at=new_access_expiry,
                refresh_expires_at=new_refresh_expiry,
                is_revoked=False,
            )
        )
        write_audit_log(
            db,
            actor_user_id=token_record.user_id,
            action="auth.token.refresh",
            entity_type="session",
            entity_id=str(token_record.id),
            details={},
        )

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_at=new_access_expiry,
    )


def logout(db: Session, user: User, refresh_token_value: str | None = None) -> None:
    with transactional_session(db):
        if refresh_token_value:
            refresh_hash = hash_token(refresh_token_value)
            token_record = db.scalar(
                select(SessionToken).where(
                    SessionToken.user_id == user.id,
                    SessionToken.refresh_token_hash == refresh_hash,
                    SessionToken.is_revoked.is_(False),
                )
            )
            if token_record:
                token_record.is_revoked = True
        else:
            active_tokens = db.scalars(
                select(SessionToken).where(
                    SessionToken.user_id == user.id,
                    SessionToken.is_revoked.is_(False),
                )
            ).all()
            for token_record in active_tokens:
                token_record.is_revoked = True

        write_audit_log(
            db,
            actor_user_id=user.id,
            action="auth.logout",
            entity_type="user",
            entity_id=str(user.id),
            details={},
        )


def change_password(db: Session, user: User, payload: ChangePasswordRequest) -> None:
    validate_password_policy(payload.new_password)
    if not verify_password(payload.old_password, user.password_hash):
        raise AuthenticationException("Old password is incorrect")

    with transactional_session(db):
        user.password_hash = hash_password(payload.new_password)
        write_audit_log(
            db,
            actor_user_id=user.id,
            action="auth.password.change",
            entity_type="user",
            entity_id=str(user.id),
            details={},
        )


def assign_role(db: Session, actor: User, user_id: int, role_id: int) -> None:
    user = db.get(User, user_id)
    role = db.get(Role, role_id)
    if user is None:
        raise NotFoundException("User not found")
    if role is None:
        raise NotFoundException("Role not found")

    existing = db.scalar(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    if existing:
        return

    with transactional_session(db):
        db.add(UserRole(user_id=user_id, role_id=role_id))
        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="auth.role.assign",
            entity_type="user_role",
            entity_id=f"{user_id}:{role_id}",
            details={},
        )


def assign_permission(db: Session, actor: User, role_id: int, permission_id: int) -> None:
    role = db.get(Role, role_id)
    permission = db.get(Permission, permission_id)
    if role is None:
        raise NotFoundException("Role not found")
    if permission is None:
        raise NotFoundException("Permission not found")

    existing = db.scalar(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
    )
    if existing:
        return

    with transactional_session(db):
        db.add(RolePermission(role_id=role_id, permission_id=permission_id))
        write_audit_log(
            db,
            actor_user_id=actor.id,
            action="auth.permission.assign",
            entity_type="role_permission",
            entity_id=f"{role_id}:{permission_id}",
            details={},
        )


def reveal_sensitive_contact(
    db: Session,
    *,
    actor: User,
    target_user_id: int,
    reason: str,
) -> str | None:
    target = db.get(User, target_user_id)
    if target is None:
        raise NotFoundException("User not found")

    encryption = FieldEncryption()
    plaintext = encryption.decrypt(target.contact_info_encrypted)

    with transactional_session(db):
        record_sensitive_access(
            db,
            actor_user_id=actor.id,
            target_user_id=target_user_id,
            field_name="contact_info",
            action="read",
            reason=reason,
        )

    return plaintext
