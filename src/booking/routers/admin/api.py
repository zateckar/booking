"""
Admin API router for frontend components
Provides API endpoints that match frontend expectations with /admin/api prefix
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any

from ...database import get_db
from ...security import get_current_admin_user
from ...timezone_service import TimezoneService
from ...email_service import EmailService
from ... import models

router = APIRouter()

# ===== TIMEZONE API =====
class TimezoneSettingsRequest(BaseModel):
    timezone: str

@router.get("/timezone/settings")
def get_timezone_settings(
    request: Request,
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get the current system timezone settings"""
    timezone_service = TimezoneService(db)
    current_tz = timezone_service.get_system_timezone()
    
    return {
        "timezone": current_tz,
        "timezone_display": current_tz.replace('_', ' ') if current_tz else 'Not set'
    }

@router.get("/timezone/timezones")
def get_available_timezones(
    request: Request,
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get list of available timezones"""
    timezone_service = TimezoneService(db)
    timezones = timezone_service.get_available_timezones()
    
    return timezones

@router.post("/timezone/settings")
def update_timezone_settings(
    req: Request,
    request: TimezoneSettingsRequest,
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update the system timezone settings"""
    try:
        timezone_service = TimezoneService(db)
        timezone_service.update_system_timezone(request.timezone)
        
        return {
            "message": "Timezone updated successfully",
            "timezone": request.timezone
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update timezone: {str(e)}")

# ===== EMAIL API =====
class EmailSettingsRequest(BaseModel):
    sendgrid_api_key: str
    from_email: str
    from_name: str
    booking_confirmation_enabled: bool
    reports_enabled: bool
    report_recipients: List[str]

@router.get("/email/settings")
def get_email_settings(
    request: Request,
    current_admin_user: models.User = Depends(get_current_admin_user),
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
        import json
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

@router.post("/email/settings")
def update_email_settings(
    req: Request,
    request: EmailSettingsRequest,
    current_admin_user: models.User = Depends(get_current_admin_user),
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
    
    import json
    settings.report_recipients = json.dumps(request.report_recipients)
    
    try:
        db.commit()
        return {"message": "Email settings updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update email settings: {str(e)}")

@router.post("/email/test-config")
def test_email_config(
    request: Request,
    current_admin_user: models.User = Depends(get_current_admin_user),
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
        email_service = EmailService(db)
        
        # Send test email to the current admin user
        result = email_service.test_email_configuration()
        
        if result['success']:
            return {"message": result['message']}
        else:
            raise HTTPException(status_code=500, detail=result['error'])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email test failed: {str(e)}")

# ===== BACKUP API =====
class BackupSettingsRequest(BaseModel):
    enabled: bool
    storage_account: str
    container_name: str
    sas_token: str
    backup_frequency: str
    backup_hour: int
    keep_backups: int

@router.get("/backup/settings")
async def get_backup_settings(
    request: Request,
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get current backup settings"""
    settings = db.query(models.BackupSettings).first()
    
    if not settings:
        # Return default settings
        return {
            "enabled": False,
            "storage_account": "",
            "container_name": "",
            "sas_token": "",
            "backup_frequency": "daily",
            "backup_hour": 2,
            "keep_backups": 30,
            "last_backup_time": None,
            "last_backup_status": "Not configured",
            "last_backup_error": None,
            "last_backup_size_mb": None
        }
    
    return {
        "enabled": settings.enabled,
        "storage_account": settings.storage_account or "",
        "container_name": settings.container_name or "",
        "sas_token": settings.sas_token or "",
        "backup_frequency": settings.backup_frequency,
        "backup_hour": settings.backup_hour,
        "keep_backups": settings.keep_backups,
        "last_backup_time": settings.last_backup_time.isoformat() if settings.last_backup_time else None,
        "last_backup_status": settings.last_backup_status,
        "last_backup_error": settings.last_backup_error,
        "last_backup_size_mb": settings.last_backup_size_mb
    }

@router.post("/backup/settings")
async def update_backup_settings(
    req: Request,
    request: BackupSettingsRequest,
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update backup settings"""
    settings = db.query(models.BackupSettings).first()
    
    if not settings:
        settings = models.BackupSettings()
        db.add(settings)
    
    # Update settings
    settings.enabled = request.enabled
    settings.storage_account = request.storage_account
    settings.container_name = request.container_name
    settings.sas_token = request.sas_token
    settings.backup_frequency = request.backup_frequency
    settings.backup_hour = request.backup_hour
    settings.keep_backups = request.keep_backups
    
    try:
        db.commit()
        return {"message": "Backup settings updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update backup settings: {str(e)}")

@router.post("/backup/test-connection")
async def test_backup_connection(
    request: Request,
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Test connection to Azure Blob Storage"""
    settings = db.query(models.BackupSettings).first()
    
    if not settings or not all([settings.storage_account, settings.container_name, settings.sas_token]):
        raise HTTPException(
            status_code=400, 
            detail="Backup settings not configured. Please set storage account, container name, and SAS token."
        )
    
    try:
        from ...backup_service import create_backup_service
        
        # Create backup service instance
        backup_service = create_backup_service(
            settings.storage_account,
            settings.container_name,
            settings.sas_token
        )
        
        # Test connection
        result = backup_service.test_connection()
        
        return result
            
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/backup/backup-now")
async def backup_now(
    request: Request,
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Trigger an immediate backup"""
    settings = db.query(models.BackupSettings).first()
    
    if not settings or not settings.enabled:
        raise HTTPException(
            status_code=400, 
            detail="Backup not enabled or settings incomplete"
        )
    
    if not all([settings.storage_account, settings.container_name, settings.sas_token]):
        raise HTTPException(
            status_code=400, 
            detail="Backup settings incomplete. Please configure all required fields."
        )
    
    try:
        # Import and trigger backup function
        from ...backup_service import perform_backup
        
        # Start backup in background
        import asyncio
        asyncio.create_task(perform_backup())
        
        return {"message": "Backup started successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start backup: {str(e)}")

@router.get("/backup/list")
async def list_backups(
    request: Request,
    limit: int = 20,
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """List existing backups in Azure Blob Storage"""
    settings = db.query(models.BackupSettings).first()
    
    if not settings or not all([settings.storage_account, settings.container_name, settings.sas_token]):
        raise HTTPException(
            status_code=400, 
            detail="Backup settings not configured"
        )
    
    try:
        from ...backup_service import create_backup_service
        
        # Create backup service instance
        backup_service = create_backup_service(
            settings.storage_account,
            settings.container_name,
            settings.sas_token
        )
        
        # List backups
        result = backup_service.list_backups(limit)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "backups": [],
            "count": 0
        }
