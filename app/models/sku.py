from sqlalchemy import Boolean, Column, Integer, String

from app.models.base import Base


class Sku(Base):
    __tablename__ = "sku_registry"

    id = Column(Integer, primary_key=True)
    trade_reference = Column(String(64), nullable=False, unique=True, index=True)
    ean = Column(String(32), nullable=True, unique=True, index=True)
    product_name = Column(String(500), nullable=False)
    is_parametrized = Column(Boolean, nullable=False, default=False, server_default="false")
