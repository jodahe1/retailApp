from typing import Any

from pydantic import BaseModel, Field


class ResponseMeta(BaseModel):
    request_id: str | None = None


class ApiResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: Any | None = None
    meta: ResponseMeta | None = None


class ApiErrorResponse(BaseModel):
    success: bool = False
    error_code: str = Field(default="INTERNAL_ERROR")
    message: str = Field(default="An internal error occurred")
    details: Any | None = None
