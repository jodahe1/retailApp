import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.base import AppException
from app.schemas.common import ApiErrorResponse

logger = logging.getLogger(__name__)


SENSITIVE_ERROR_CODES = {"AUTHENTICATION_ERROR", "AUTHORIZATION_ERROR", "SECURITY_ERROR"}


def _error_payload(*, error_code: str, message: str, details: object | None = None) -> dict:
    return ApiErrorResponse(error_code=error_code, message=message, details=details).model_dump()


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        if exc.error_code in SENSITIVE_ERROR_CODES:
            logger.warning(
                "security_error path=%s code=%s",
                request.url.path,
                exc.error_code,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(error_code=exc.error_code, message=exc.message, details=exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info("request_validation_failed path=%s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_payload(
                error_code="VALIDATION_ERROR",
                message="Request validation failed",
                details=exc.errors(),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {
            status.HTTP_401_UNAUTHORIZED: "AUTHENTICATION_ERROR",
            status.HTTP_403_FORBIDDEN: "AUTHORIZATION_ERROR",
            status.HTTP_404_NOT_FOUND: "NOT_FOUND",
            status.HTTP_409_CONFLICT: "CONFLICT",
        }
        error_code = code_map.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(error_code=error_code, message=str(exc.detail), details=None),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception path=%s", request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload(error_code="INTERNAL_ERROR", message="An internal error occurred"),
        )
