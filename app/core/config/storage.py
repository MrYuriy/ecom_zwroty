from pydantic import Field

from app.core.config.base import BaseConfig


class StorageConfig(BaseConfig):
    # Relative paths resolve against the working directory; in docker this is a mounted volume.
    UPLOADS_DIR: str = Field("uploads", alias="UPLOADS_DIR")
    MAX_IMAGE_MB: int = Field(15, alias="MAX_IMAGE_MB")
    MAX_IMAGES_PER_LINE: int = Field(10, alias="MAX_IMAGES_PER_LINE")
