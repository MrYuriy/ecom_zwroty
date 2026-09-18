from app.core.config.base import BaseConfig
from app.core.config.db import DbBaseConfig
from app.core.config.jwt import JwtConfig

__all__ = ["Settings", "settings"]


class Settings(BaseConfig):
    db: DbBaseConfig = DbBaseConfig()
    jwt: JwtConfig = JwtConfig()


settings = Settings()
