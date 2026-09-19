from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.enums.user import RoleEnum


class UserCreate(BaseModel):
    wms_login: str = Field(min_length=1, max_length=64)
    password: str
    full_name: str = Field(min_length=1, max_length=255)
    role: RoleEnum = RoleEnum.OPERATOR

    @field_validator("wms_login")
    @classmethod
    def _strip_login(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("WMS login must not be blank")
        return value


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    role: RoleEnum | None = None
    is_active: bool | None = None
    password: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    wms_login: str
    full_name: str
    role: RoleEnum
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    wms_login: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
