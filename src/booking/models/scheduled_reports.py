from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .base import BaseModel, TimezoneAwareDateTime


class ScheduledDynamicReport(BaseModel):
    __tablename__ = "scheduled_dynamic_reports"

    name = Column(String, index=True)  # User-friendly name for the schedule
    description = Column(String)
    template_id = Column(Integer, ForeignKey("report_templates.id"))
    recipients = Column(String)  # JSON array of email addresses
    frequency = Column(String)  # "daily", "weekly", "monthly"
    schedule_hour = Column(Integer, default=9)  # Hour in 24h format
    timezone = Column(String, default="UTC")
    is_enabled = Column(Boolean, default=True)
    include_excel = Column(Boolean, default=True)
    months_period = Column(Integer, default=2)  # How many months of data to include
    
    # Tracking fields
    last_sent = Column(TimezoneAwareDateTime, nullable=True)
    last_error = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(TimezoneAwareDateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TimezoneAwareDateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    template = relationship("ReportTemplate")
    creator = relationship("User")
