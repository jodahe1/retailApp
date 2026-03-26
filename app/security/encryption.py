from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.exceptions.base import SecurityException


class FieldEncryption:
    def __init__(self) -> None:
        settings = get_settings()
        self._fernet = Fernet(settings.field_encryption_key.encode("utf-8"))

    def encrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise SecurityException("Unable to decrypt field") from exc
