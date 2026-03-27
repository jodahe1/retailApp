from datetime import datetime

from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, examples=["cashier01"])
    password: str = Field(min_length=8, max_length=128, examples=["Admin1234"])
    id_number: str | None = Field(default=None, examples=["ID-ETH-12345678"])
    contact_info: str | None = Field(default=None, examples=["+251900000000"])


class LoginRequest(BaseModel):
    username: str = Field(examples=["cashier01"])
    password: str = Field(examples=["Admin1234"])


class TokenResponse(BaseModel):
    access_token: str = Field(examples=["kY9...access...token"])
    refresh_token: str = Field(examples=["xB2...refresh...token"])
    token_type: str = Field(default="bearer", examples=["bearer"])
    expires_at: datetime


class RefreshRequest(BaseModel):
    refresh_token: str = Field(examples=["xB2...refresh...token"])


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, examples=["xB2...refresh...token"])


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(examples=["Admin1234"])
    new_password: str = Field(min_length=8, max_length=128, examples=["NewAdmin1234"])


class RoleAssignmentRequest(BaseModel):
    user_id: int = Field(examples=[12])
    role_id: int = Field(examples=[3])


class PermissionAssignmentRequest(BaseModel):
    role_id: int = Field(examples=[3])
    permission_id: int = Field(examples=[8])
