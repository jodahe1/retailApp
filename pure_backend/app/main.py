from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db import models  # noqa: F401
from app.exceptions.handlers import register_exception_handlers

settings = get_settings()
setup_logging(settings)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=(
            "Offline-first middle-platform API for retail checkout and entrepreneurship incubation. "
            "Includes identity/auth/security baseline with role-permission authorization."
        ),
        debug=settings.debug,
        version="0.2.0",
        contact={"name": "Platform Team", "email": "platform@example.local"},
        license_info={"name": "Proprietary - Internal Use"},
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get(
        "/",
        tags=["system"],
        summary="Root Service Info",
        description="Simple root endpoint with service name and current API version.",
    )
    async def root() -> dict[str, str]:
        return {"service": settings.app_name, "version": "0.2.0"}

    return app


app = create_app()
