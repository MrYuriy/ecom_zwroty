from app.core.config.base import BaseConfig
from app.core.config.db import DbBaseConfig
from app.core.config.google import GoogleConfig
from app.core.config.jwt import JwtConfig
from app.core.config.storage import StorageConfig

__all__ = ["Settings", "settings"]


class Settings(BaseConfig):
    db: DbBaseConfig = DbBaseConfig()
    jwt: JwtConfig = JwtConfig()
    storage: StorageConfig = StorageConfig()
    google: GoogleConfig = GoogleConfig()


settings = Settings()
