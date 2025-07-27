from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.types import TypeDecorator
from sqlalchemy.sql import func
from datetime import datetime, timezone

from ..database import Base


class TimezoneAwareDateTime(TypeDecorator):
    """A DateTime type that ensures all datetime values are timezone-aware (UTC)"""
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                # If naive datetime, assume UTC
                value = value.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC if not already
                value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            # Ensure returned datetime is timezone-aware (UTC)
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
        return value


class BaseModel(Base):
    """Base model class with common fields"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(TimezoneAwareDateTime, default=func.now(), nullable=False)
    updated_at = Column(TimezoneAwareDateTime, default=func.now(), onupdate=func.now(), nullable=False)
