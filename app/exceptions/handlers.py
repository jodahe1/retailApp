import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status

from app.exceptions.base import AppException
from app.schemas.common import ApiErrorResponse

logger = logging.getLogger(__name__)


SENSITIVE_ERROR_CODES = {"AUTHENTICATION_ERROR", "AUTHORIZATION_ERROR", "SECURITY_ERROR"}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        if exc.error_code in SENSITIVE_ERROR_CODES:
            logger.warning(
                "Security exception path=%s code=%s",
                request.url.path,
                exc.error_code,
            )
        payload = ApiErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception path=%s", request.url.path, exc_info=exc)
        payload = ApiErrorResponse()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=payload.model_dump(),
        )
