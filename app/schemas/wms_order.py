from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WmsOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bo_wms_number: str
    tempo_number: str | None
    created_at: datetime


class WmsSyncResult(BaseModel):
    rows: int
    added: int
