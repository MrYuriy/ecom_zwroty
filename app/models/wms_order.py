from sqlalchemy import Column, Index, String

from app.models.base import Base, CreatedAtMixin


class WmsOrder(Base, CreatedAtMixin):
    """BO/WMS → Tempo number pairs imported from the WMS Google Sheet.

    created_at (from CreatedAtMixin) is when the pair was first imported; it drives cleanup of stale orders.
    """

    __tablename__ = "wms_orders"
    __table_args__ = (Index("ix_wms_orders_created_at", "created_at"),)

    bo_wms_number = Column(String(64), primary_key=True)
    tempo_number = Column(String(64), nullable=True)
