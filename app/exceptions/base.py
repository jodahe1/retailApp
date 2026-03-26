from typing import Any


class AppException(Exception):
    def __init__(self, message: str, error_code: str = "APP_ERROR", details: Any | None = None):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(message)
