from collections.abc import Callable
from datetime import datetime, timezone

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.exceptions.base import AuthenticationException, AuthorizationException
from app.models.identity import Role, SessionToken, User
from app.security.tokens import hash_token

bearer_scheme = HTTPBearer(auto_error=False)


def _is_expired(dt: datetime) -> bool:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt < datetime.now(timezone.utc)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationException("Authentication required")

    token_hash = hash_token(credentials.credentials)
    token_record = db.scalar(select(SessionToken).where(SessionToken.token_hash == token_hash))
    if token_record is None or token_record.is_revoked or _is_expired(token_record.expires_at):
        raise AuthenticationException("Invalid or expired token")

    user = db.scalar(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == token_record.user_id)
    )
    if user is None or not user.is_active or user.is_deleted:
        raise AuthenticationException("User account not available")

    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active or user.is_deleted:
        raise AuthenticationException("Inactive account")
    return user


def require_permission(permission_code: str) -> Callable:
    def dependency(user: User = Depends(get_current_active_user)) -> User:
        if user.is_superuser:
            return user

        permission_codes = {perm.code for role in user.roles for perm in role.permissions}
        if permission_code not in permission_codes:
            raise AuthorizationException("Permission denied")
        return user

    return dependency


def require_superuser(user: User = Depends(get_current_active_user)) -> User:
    if not user.is_superuser:
        raise AuthorizationException("Admin permission required")
    return user
