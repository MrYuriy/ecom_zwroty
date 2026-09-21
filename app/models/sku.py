from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base, CreatedAtMixin


class Sku(Base):
    __tablename__ = "sku_registry"

    id = Column(Integer, primary_key=True)
    trade_reference = Column(String(64), nullable=False, unique=True, index=True)
    product_name = Column(String(500), nullable=False)
    is_parametrized = Column(Boolean, nullable=False, default=False, server_default="false")

    # Loaded with every SKU (async sessions can't lazy-load); a product has a handful of codes at most.
    eans = relationship(
        "SkuEan",
        back_populates="sku",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SkuEan.ean",
    )


class SkuEan(Base, CreatedAtMixin):
    """A scannable code of a product. One product has many codes; each code leads to exactly one product."""

    __tablename__ = "sku_eans"

    id = Column(Integer, primary_key=True)
    ean = Column(String(32), nullable=False, unique=True, index=True)
    sku_id = Column(Integer, ForeignKey("sku_registry.id", ondelete="CASCADE"), nullable=False, index=True)

    sku = relationship("Sku", back_populates="eans")
