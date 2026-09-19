from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

_MAX_ACK = 1000


class ReportLineItem(BaseModel):
    line_uuid: UUID
    row: list[str | int]


class ReportLinesOut(BaseModel):
    columns: list[str]
    items: list[ReportLineItem]
    remaining: int


class ImageItem(BaseModel):
    image_uuid: UUID
    file_name: str
    content_type: str
    size_bytes: int
    url: str
    line_uuid: UUID
    return_date: date
    bo_wms_number: str
    trade_reference: str


class ImagesOut(BaseModel):
    items: list[ImageItem]
    remaining: int


class LinesAck(BaseModel):
    line_uuids: list[UUID] = Field(min_length=1, max_length=_MAX_ACK)


class ImagesAck(BaseModel):
    image_uuids: list[UUID] = Field(min_length=1, max_length=_MAX_ACK)


class AckResult(BaseModel):
    acknowledged: int
