from pydantic import Field

from app.core.config.base import BaseConfig


class GoogleConfig(BaseConfig):
    # Service-account key; the sheet must be shared with its client_email.
    CREDENTIALS_FILE: str = Field("creds.json", alias="GOOGLE_CREDENTIALS_FILE")
    WMS_SHEET_ID: str = Field("", alias="WMS_SHEET_ID")
    WMS_SHEET_GID: int = Field(0, alias="WMS_SHEET_GID")
    WMS_SYNC_ENABLED: bool = Field(False, alias="WMS_SYNC_ENABLED")
    WMS_SYNC_INTERVAL_MINUTES: int = Field(60, alias="WMS_SYNC_INTERVAL_MINUTES")
