from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .base import BaseModel, TimezoneAwareDateTime


class DynamicReportTemplate(BaseModel):
    __tablename__ = "dynamic_report_templates"

    name = Column(String, index=True)
    description = Column(String)
    selected_columns = Column(String)  # JSON array of column names
    is_default = Column(Boolean, default=False)
    created_at = Column(TimezoneAwareDateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TimezoneAwareDateTime, default=lambda: datetime.now(timezone.utc))


class ReportColumn(BaseModel):
    __tablename__ = "report_columns"

    column_name = Column(String, unique=True, index=True)
    display_label = Column(String)
    column_type = Column(String)  # "static", "mapped", "calculated"
    data_type = Column(String)  # "string", "number", "boolean", "array", "date"
    is_available = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)


class ReportTemplate(BaseModel):
    __tablename__ = "report_templates"

    name = Column(String, index=True)
    description = Column(String)
    selected_columns = Column(String)  # JSON array of column names
    is_default = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(TimezoneAwareDateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(TimezoneAwareDateTime, default=lambda: datetime.now(timezone.utc))

    creator = relationship("User")
