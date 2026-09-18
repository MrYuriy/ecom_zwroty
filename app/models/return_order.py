from datetime import date

from sqlalchemy import CheckConstraint, Column, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.enums.return_order import CarrierType, GoodsCondition
from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDMixin, UUIDType


class ReturnOrder(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "return_orders"

    # NULL means the order had no number ("brak" in the report); numbers may repeat across returns.
    bo_wms_number = Column(String(64), nullable=True, index=True)
    tempo_number = Column(String(64), nullable=True, index=True)
    return_date = Column(Date, nullable=False, default=date.today, index=True)
    operator_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    operator = relationship("User", back_populates="return_orders")
    lines = relationship(
        "OrderLine",
        back_populates="return_order",
        cascade="all, delete-orphan",
        order_by="OrderLine.created_at",
    )


class OrderLine(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "order_lines"
    __table_args__ = (CheckConstraint("quantity >= 1", name="ck_order_lines_quantity_positive"),)

    return_order_uuid = Column(
        UUIDType, ForeignKey("return_orders.uuid", ondelete="CASCADE"), nullable=False, index=True
    )
    sku_id = Column(Integer, ForeignKey("sku_registry.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    carrier_type = Column(Enum(CarrierType, name="carrier_type_enum"), nullable=False)
    goods_condition = Column(Enum(GoodsCondition, name="goods_condition_enum"), nullable=False)
    damage_description = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)

    return_order = relationship("ReturnOrder", back_populates="lines")
    sku = relationship("Sku")
    images = relationship(
        "LineImage",
        back_populates="line",
        cascade="all, delete-orphan",
        order_by="LineImage.created_at",
    )
