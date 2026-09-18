from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base, CreatedAtMixin, UUIDMixin, UUIDType


class LineImage(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "line_images"

    order_line_uuid = Column(UUIDType, ForeignKey("order_lines.uuid", ondelete="CASCADE"), nullable=False, index=True)
    # Name of the file inside the uploads directory; never a client-supplied path.
    file_name = Column(String(64), nullable=False, unique=True)
    content_type = Column(String(32), nullable=False)
    size_bytes = Column(Integer, nullable=False)

    line = relationship("OrderLine", back_populates="images")
