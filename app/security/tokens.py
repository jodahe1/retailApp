import hashlib
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings


settings = get_settings()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_access_expiry() -> datetime:
    return utcnow() + timedelta(minutes=settings.access_token_minutes)


def build_refresh_expiry() -> datetime:
    return utcnow() + timedelta(minutes=settings.refresh_token_minutes)
