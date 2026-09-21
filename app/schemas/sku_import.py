from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.enums.sku_import import SkuImportStatus


class SkuImportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    file_name: str
    status: SkuImportStatus
    stage: str | None
    rows_read: int
    rows_skipped: int
    skus_created: int
    skus_updated: int
    eans_created: int
    eans_reassigned: int
    error: str | None
    created_at: datetime
    finished_at: datetime | None
