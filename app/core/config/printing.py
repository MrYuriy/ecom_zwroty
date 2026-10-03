from pydantic import Field

from app.core.config.base import BaseConfig


class PrintingConfig(BaseConfig):
    """Zebra labels for closed returns, handed to the cups server an ESP printer polls."""

    # Empty = nothing is printed (the app works exactly as before).
    LABELS_URL: str = Field("", alias="CUPS_LABELS_URL")
    TIMEOUT_SECONDS: float = Field(5.0, alias="CUPS_TIMEOUT_SECONDS")
