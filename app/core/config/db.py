from urllib.parse import urlsplit, urlunsplit

from pydantic import Field

from app.core.config.base import BaseConfig


class DbBaseConfig(BaseConfig):
    DATABASE_URL: str = Field(..., alias="DATABASE_URL")
    ECHO: bool = Field(False, alias="DB_ECHO")

    @property
    def url(self) -> str:
        """Async SQLAlchemy URL: postgres → asyncpg (libpq-only query params dropped), sqlite → aiosqlite."""
        raw = self.DATABASE_URL
        if raw.startswith(("postgres://", "postgresql://")):
            parts = urlsplit(raw)
            return urlunsplit(("postgresql+asyncpg", parts.netloc, parts.path, "", ""))
        if raw.startswith("sqlite://") and "+aiosqlite" not in raw:
            return raw.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return raw

    @property
    def connect_args(self) -> dict:
        # asyncpg takes TLS here, not in the URL; a local docker Postgres opts out with sslmode=disable.
        if not self.url.startswith("postgresql+asyncpg"):
            return {}
        if "sslmode=disable" in self.DATABASE_URL:
            return {}
        return {"ssl": True}
