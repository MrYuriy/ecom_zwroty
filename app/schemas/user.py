from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.enums.user import RoleEnum


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str = Field(min_length=1, max_length=255)
    role: RoleEnum = RoleEnum.OPERATOR

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return value.lower()


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    role: RoleEnum | None = None
    is_active: bool | None = None
    password: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: RoleEnum
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
