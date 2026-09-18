from uuid import uuid4

from sqlalchemy import Column, DateTime, Uuid, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Native UUID on Postgres, portable variant so the test suite runs the same models on sqlite.
UUIDType = PGUUID(as_uuid=True).with_variant(Uuid(), "sqlite")


class UUIDMixin:
    uuid = Column(UUIDType, primary_key=True, default=uuid4)


class CreatedAtMixin:
    created_at = Column(DateTime, default=func.now(), server_default=func.now(), nullable=False)


class TimestampMixin(CreatedAtMixin):
    updated_at = Column(DateTime, default=func.now(), server_default=func.now(), onupdate=func.now(), nullable=False)
