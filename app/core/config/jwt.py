from pydantic import Field

from app.core.config.base import BaseConfig


class JwtConfig(BaseConfig):
    SECRET_KEY: str = Field("dev-secret-change-me", alias="JWT_SECRET_KEY")
    ALGORITHM: str = Field("HS256", alias="JWT_ALGORITHM")
    # One warehouse shift, so an operator is not logged out mid-work.
    EXPIRE_MINUTES: int = Field(720, alias="JWT_EXPIRE_MINUTES")
