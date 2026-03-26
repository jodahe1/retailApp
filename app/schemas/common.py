from typing import Any

from pydantic import BaseModel, Field


class ResponseMeta(BaseModel):
    request_id: str | None = Field(default=None, examples=["req_01HR4YJ8M1K7C8QW2N4A6E9T0P"])


class ApiResponse(BaseModel):
    success: bool = Field(default=True, examples=[True])
    message: str = Field(default="OK", examples=["Operation completed successfully"])
    data: Any | None = Field(default=None)
    meta: ResponseMeta | None = Field(default=None)


class ApiErrorResponse(BaseModel):
    success: bool = Field(default=False, examples=[False])
    error_code: str = Field(default="INTERNAL_ERROR", examples=["AUTHENTICATION_ERROR"])
    message: str = Field(default="An internal error occurred", examples=["Invalid credentials"])
    details: Any | None = Field(default=None)
