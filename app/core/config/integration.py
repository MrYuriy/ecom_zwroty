from pydantic import Field

from app.core.config.base import BaseConfig


class IntegrationConfig(BaseConfig):
    # Shared secret for external scripts (Google Apps Script); empty = integration API disabled.
    API_KEY: str = Field("", alias="INTEGRATION_API_KEY")
    # Public origin used in links handed to scripts (behind Cloudflare the app can't see it itself).
    PUBLIC_BASE_URL: str = Field("", alias="PUBLIC_BASE_URL")
