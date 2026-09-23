from sqlalchemy import Column, Date, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class WorkLog(Base, TimestampMixin):
    """Minutes spent verifying returns on one day — one record per day, printed on the daily form."""

    __tablename__ = "work_logs"

    work_date = Column(Date, primary_key=True)
    minutes = Column(Integer, nullable=False)
    # Who saved it last; the record itself belongs to the day, not to a person.
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    author = relationship("User")
