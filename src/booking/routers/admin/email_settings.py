from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

from ... import models, schemas
from ...database import get_db
from ...email_service import EmailService
from ...logging_config import get_logger
from ...security import get_current_admin_user

logger = get_logger("admin.email_settings")

router = APIRouter()


@router.get("/email-settings", response_model=schemas.EmailSettings)
def get_email_settings(
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get current email settings"""
    settings = db.query(models.EmailSettings).first()
    if not settings:
        # Create default settings if none exist
        settings = models.EmailSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    # Convert JSON string to list for report_recipients
    if settings.report_recipients:
        try:
            recipients_list = json.loads(settings.report_recipients) if isinstance(settings.report_recipients, str) else []
        except (json.JSONDecodeError, TypeError):
            recipients_list = []
    else:
        recipients_list = []
    
    # Create response with proper format
    response_data = {
        "id": settings.id,
        "sendgrid_api_key": settings.sendgrid_api_key,
        "from_email": settings.from_email,
        "from_name": settings.from_name,
        "booking_confirmation_enabled": settings.booking_confirmation_enabled,
        "reports_enabled": settings.reports_enabled,
        "report_recipients": recipients_list,
        "report_schedule_hour": settings.report_schedule_hour,
        "report_frequency": settings.report_frequency,
        "last_report_sent": settings.last_report_sent,
        "timezone": settings.timezone or "UTC"
    }
    
    return schemas.EmailSettings(**response_data)


@router.put("/email-settings", response_model=schemas.EmailSettings)
def update_email_settings(
    settings_update: schemas.EmailSettingsUpdate,
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update email settings"""
    settings = db.query(models.EmailSettings).first()
    if not settings:
        settings = models.EmailSettings()
        db.add(settings)
    
    # Update fields if provided
    if settings_update.sendgrid_api_key is not None:
        settings.sendgrid_api_key = settings_update.sendgrid_api_key
    if settings_update.from_email is not None:
        settings.from_email = settings_update.from_email
    if settings_update.from_name is not None:
        settings.from_name = settings_update.from_name
    if settings_update.booking_confirmation_enabled is not None:
        settings.booking_confirmation_enabled = settings_update.booking_confirmation_enabled
    if settings_update.reports_enabled is not None:
        settings.reports_enabled = settings_update.reports_enabled
    if settings_update.report_recipients is not None:
        # Convert list to JSON string for storage
        settings.report_recipients = json.dumps(settings_update.report_recipients)
    if settings_update.report_schedule_hour is not None:
        if not (0 <= settings_update.report_schedule_hour <= 23):
            raise HTTPException(status_code=400, detail="Report schedule hour must be between 0 and 23")
        settings.report_schedule_hour = settings_update.report_schedule_hour
    if settings_update.report_frequency is not None:
        if settings_update.report_frequency not in ["daily", "weekly", "monthly"]:
            raise HTTPException(status_code=400, detail="Report frequency must be 'daily', 'weekly', or 'monthly'")
        settings.report_frequency = settings_update.report_frequency
    if settings_update.timezone is not None:
        # Validate timezone
        import pytz
        try:
            pytz.timezone(settings_update.timezone)
            old_timezone = settings.timezone or "UTC"
            if old_timezone != settings_update.timezone:
                logger.info(f"Timezone changed from {old_timezone} to {settings_update.timezone}")
                # Clear timezone cache in timezone service
                from ...timezone_service import TimezoneService
                timezone_service = TimezoneService(db)
                timezone_service.refresh_timezone_cache()
            settings.timezone = settings_update.timezone
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Invalid timezone attempted: {settings_update.timezone}")
            raise HTTPException(status_code=400, detail=f"Invalid timezone: {settings_update.timezone}")
    
    db.commit()
    db.refresh(settings)
    
    # Convert JSON string back to list for response
    if settings.report_recipients:
        try:
            recipients_list = json.loads(settings.report_recipients) if isinstance(settings.report_recipients, str) else []
        except (json.JSONDecodeError, TypeError):
            recipients_list = []
    else:
        recipients_list = []
    
    response_data = {
        "id": settings.id,
        "sendgrid_api_key": settings.sendgrid_api_key,
        "from_email": settings.from_email,
        "from_name": settings.from_name,
        "booking_confirmation_enabled": settings.booking_confirmation_enabled,
        "reports_enabled": settings.reports_enabled,
        "report_recipients": recipients_list,
        "report_schedule_hour": settings.report_schedule_hour,
        "report_frequency": settings.report_frequency,
        "last_report_sent": settings.last_report_sent,
        "timezone": settings.timezone or "UTC"
    }
    
    return schemas.EmailSettings(**response_data)


@router.post("/email-settings/test")
def test_email_configuration(
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Test email configuration by sending a test email"""
    email_service = EmailService(db)
    result = email_service.test_email_configuration()
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return {"message": result['message']}


@router.post("/email-settings/send-report")
def send_report_now(
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Manually trigger sending of booking report"""
    email_service = EmailService(db)
    success = email_service.send_booking_report(force_send=True)
    
    if not success:
        raise HTTPException(status_code=400, detail="Failed to send report. Check email settings and logs.")
    
    return {"message": "Report sent successfully"}
