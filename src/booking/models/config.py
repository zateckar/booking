from sqlalchemy import Boolean, Column, Integer, String
from datetime import datetime, timezone

from .base import BaseModel, TimezoneAwareDateTime


class AppConfig(BaseModel):
    __tablename__ = "app_config"

    config_key = Column(String, unique=True, index=True)
    config_value = Column(String)
    description = Column(String)


class BackupSettings(BaseModel):
    __tablename__ = "backup_settings"

    enabled = Column(Boolean, default=False)
    storage_account = Column(String)
    container_name = Column(String)
    sas_token = Column(String)
    backup_frequency = Column(String, default="daily")
    backup_hour = Column(Integer, default=2)
    keep_backups = Column(Integer, default=30)
    last_backup_time = Column(TimezoneAwareDateTime)
    last_backup_status = Column(String)
    last_backup_size_mb = Column(Integer)
    last_backup_error = Column(String)


class EmailSettings(BaseModel):
    __tablename__ = "email_settings"

    sendgrid_api_key = Column(String)
    from_email = Column(String)
    from_name = Column(String)
    booking_confirmation_enabled = Column(Boolean, default=False)
    reports_enabled = Column(Boolean, default=False)
    report_recipients = Column(String)  # JSON array of email addresses
    report_schedule_hour = Column(Integer, default=9)
    report_frequency = Column(String, default="weekly")
    last_report_sent = Column(TimezoneAwareDateTime)
    timezone = Column(String, default="UTC")  # Timezone for report scheduling
    # Dynamic reports scheduling
    dynamic_reports_enabled = Column(Boolean, default=False)
    dynamic_report_recipients = Column(String)  # JSON array of email addresses
    dynamic_report_schedule_hour = Column(Integer, default=9)
    dynamic_report_frequency = Column(String, default="weekly")
    dynamic_report_template_id = Column(Integer)  # ID of the template to use for scheduled reports
    last_dynamic_report_sent = Column(TimezoneAwareDateTime)
