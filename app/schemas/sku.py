from pydantic import BaseModel, ConfigDict, Field


class SkuCreate(BaseModel):
    trade_reference: str = Field(min_length=1, max_length=64)
    ean: str | None = Field(None, max_length=32)
    product_name: str = Field(min_length=1, max_length=500)
    is_parametrized: bool = False


class SkuUpdate(BaseModel):
    trade_reference: str | None = Field(None, min_length=1, max_length=64)
    ean: str | None = Field(None, max_length=32)
    product_name: str | None = Field(None, min_length=1, max_length=500)
    is_parametrized: bool | None = None


class SkuOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trade_reference: str
    ean: str | None
    product_name: str
    is_parametrized: bool
