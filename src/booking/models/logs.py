from sqlalchemy import Column, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .base import BaseModel, TimezoneAwareDateTime


class LogEntry(BaseModel):
    __tablename__ = "log_entries"

    timestamp = Column(TimezoneAwareDateTime, default=lambda: datetime.now(timezone.utc), index=True)
    level = Column(String, index=True)
    logger_name = Column(String, index=True)
    message = Column(Text)
    module = Column(String, nullable=True)
    function = Column(String, nullable=True)
    line_number = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    request_id = Column(String, nullable=True, index=True)
    extra_data = Column(JSON, nullable=True)
    
    user = relationship("User")
