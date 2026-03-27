import re
import secrets

from passlib.context import CryptContext

from app.exceptions.base import ValidationException

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


PASSWORD_MIN_LENGTH = 8


def validate_password_policy(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValidationException("Password must be at least 8 characters long")

    has_letter = bool(re.search(r"[A-Za-z]", password))
    has_number = bool(re.search(r"\d", password))
    if not (has_letter and has_number):
        raise ValidationException("Password must include both letters and numbers")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def generate_token() -> str:
    return secrets.token_urlsafe(48)
