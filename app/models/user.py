from sqlalchemy import Boolean, Column, Enum, Integer, String
from sqlalchemy.orm import relationship

from app.enums.user import RoleEnum
from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    wms_login = Column(String(64), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum, name="role_enum"), nullable=False, default=RoleEnum.OPERATOR)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    return_orders = relationship("ReturnOrder", back_populates="operator")
