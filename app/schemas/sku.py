from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.enums.return_order import ReturnStatus

_MAX_EAN_LENGTH = 32


def clean_eans(values: list[str] | None) -> list[str] | None:
    """Trim, drop blanks and duplicates (keeping order)."""
    if values is None:
        return None
    cleaned: list[str] = []
    for value in values:
        code = (value or "").strip()
        if not code or code in cleaned:
            continue
        if len(code) > _MAX_EAN_LENGTH:
            raise ValueError(f"EAN longer than {_MAX_EAN_LENGTH} characters: {code}")
        cleaned.append(code)
    return cleaned


class SkuCreate(BaseModel):
    trade_reference: str = Field(min_length=1, max_length=64)
    eans: list[str] = Field(default_factory=list)
    product_name: str = Field(min_length=1, max_length=500)
    is_parametrized: bool = False

    @field_validator("eans")
    @classmethod
    def _clean(cls, value: list[str] | None) -> list[str] | None:
        return clean_eans(value)


class SkuUpdate(BaseModel):
    trade_reference: str | None = Field(None, min_length=1, max_length=64)
    # None keeps the codes as they are; a list replaces them (an empty list removes all).
    eans: list[str] | None = None
    product_name: str | None = Field(None, min_length=1, max_length=500)
    is_parametrized: bool | None = None

    @field_validator("eans")
    @classmethod
    def _clean(cls, value: list[str] | None) -> list[str] | None:
        return clean_eans(value)


class SkuOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trade_reference: str
    eans: list[str]
    product_name: str
    is_parametrized: bool

    @field_validator("eans", mode="before")
    @classmethod
    def _codes(cls, value: list) -> list[str]:
        return [item if isinstance(item, str) else item.ean for item in value]


class SkuUsageOut(BaseModel):
    """A return that uses the SKU (so the SKU can't be deleted)."""

    uuid: UUID
    bo_wms_number: str | None
    tempo_number: str | None
    return_date: date
    status: ReturnStatus
    lines: int
