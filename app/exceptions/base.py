from typing import Any


class AppException(Exception):
    status_code: int = 400

    def __init__(self, message: str, error_code: str = "APP_ERROR", details: Any | None = None):
        self.message = message
        self.error_code = error_code
        self.details = details
        super().__init__(message)


class ValidationException(AppException):
    status_code = 422

    def __init__(self, message: str, details: Any | None = None):
        super().__init__(message=message, error_code="VALIDATION_ERROR", details=details)


class AuthenticationException(AppException):
    status_code = 401

    def __init__(self, message: str = "Authentication failed", details: Any | None = None):
        super().__init__(message=message, error_code="AUTHENTICATION_ERROR", details=details)


class AuthorizationException(AppException):
    status_code = 403

    def __init__(self, message: str = "Permission denied", details: Any | None = None):
        super().__init__(message=message, error_code="AUTHORIZATION_ERROR", details=details)


class NotFoundException(AppException):
    status_code = 404

    def __init__(self, message: str = "Resource not found", details: Any | None = None):
        super().__init__(message=message, error_code="NOT_FOUND", details=details)


class ConflictException(AppException):
    status_code = 409

    def __init__(self, message: str = "Conflict", details: Any | None = None):
        super().__init__(message=message, error_code="CONFLICT", details=details)


class SecurityException(AppException):
    status_code = 423

    def __init__(self, message: str = "Security policy violation", details: Any | None = None):
        super().__init__(message=message, error_code="SECURITY_ERROR", details=details)
