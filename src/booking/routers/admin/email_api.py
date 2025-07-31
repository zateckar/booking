"""
Email API endpoints for admin interface
Provides REST API endpoints that match the frontend expectations
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import json

from ...database import get_db
from ...security import get_current_admin_user
from ... import models

router = APIRouter()


class EmailSettingsRequest(BaseModel):
    sendgrid_api_key: str
    from_email: str
    from_name: str
    booking_confirmation_enabled: bool
    reports_enabled: bool
    report_recipients: List[str]


@router.get("/settings")
def get_email_settings(
    db: Session = Depends(get_db)
):
    """Get current email settings"""
    settings = db.query(models.EmailSettings).first()
    
    if not settings:
        # Return default settings
        return {
            "sendgrid_api_key": "",
            "from_email": "",
            "from_name": "",
            "booking_confirmation_enabled": False,
            "reports_enabled": False,
            "report_recipients": []
        }
    
    # Parse report recipients from JSON string
    try:
        recipients = json.loads(settings.report_recipients) if settings.report_recipients else []
    except:
        recipients = []
    
    return {
        "sendgrid_api_key": settings.sendgrid_api_key or "",
        "from_email": settings.from_email or "",
        "from_name": settings.from_name or "",
        "booking_confirmation_enabled": settings.booking_confirmation_enabled or False,
        "reports_enabled": settings.reports_enabled or False,
        "report_recipients": recipients
    }


@router.post("/settings")
def update_email_settings(
    request: EmailSettingsRequest,
    db: Session = Depends(get_db)
):
    """Update email settings"""
    settings = db.query(models.EmailSettings).first()
    
    if not settings:
        settings = models.EmailSettings()
        db.add(settings)
    
    # Update settings
    settings.sendgrid_api_key = request.sendgrid_api_key
    settings.from_email = request.from_email
    settings.from_name = request.from_name
    settings.booking_confirmation_enabled = request.booking_confirmation_enabled
    settings.reports_enabled = request.reports_enabled
    settings.report_recipients = json.dumps(request.report_recipients)
    
    try:
        db.commit()
        return {"message": "Email settings updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update email settings: {str(e)}")


@router.post("/test-config")
def test_email_config(
    db: Session = Depends(get_db)
):
    """Test email configuration by sending a test email"""
    settings = db.query(models.EmailSettings).first()
    
    if not settings or not settings.sendgrid_api_key or not settings.from_email:
        raise HTTPException(
            status_code=400,
            detail="Email settings not configured. Please set SendGrid API key and from email."
        )
    
    try:
        from ...email_service import EmailService
        
        email_service = EmailService(db)
        
        # Send test email to a default admin email or use a placeholder
        success = email_service.send_test_email(
            to_email="admin@example.com",  # This should be updated to get current user properly
            admin_name="Admin"
        )
        
        if success:
            return {"message": f"Test email sent successfully to {current_admin_user.email}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send test email")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email test failed: {str(e)}")