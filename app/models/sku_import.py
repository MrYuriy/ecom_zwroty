from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text

from app.enums.sku_import import SkuImportStatus
from app.models.base import Base, TimestampMixin, UUIDMixin


class SkuImport(Base, UUIDMixin, TimestampMixin):
    """One upload of the SKU/EAN file; runs in the background and reports progress here."""

    __tablename__ = "sku_imports"

    file_name = Column(String(255), nullable=False)
    status = Column(
        Enum(SkuImportStatus, name="sku_import_status_enum"),
        nullable=False,
        default=SkuImportStatus.PENDING,
        server_default=SkuImportStatus.PENDING.value,
    )
    stage = Column(String(64), nullable=True)
    rows_read = Column(Integer, nullable=False, default=0, server_default="0")
    rows_skipped = Column(Integer, nullable=False, default=0, server_default="0")
    skus_created = Column(Integer, nullable=False, default=0, server_default="0")
    skus_updated = Column(Integer, nullable=False, default=0, server_default="0")
    eans_created = Column(Integer, nullable=False, default=0, server_default="0")
    eans_reassigned = Column(Integer, nullable=False, default=0, server_default="0")
    error = Column(Text, nullable=True)
    started_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    finished_at = Column(DateTime, nullable=True)
