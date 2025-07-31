"""
Timezone API endpoints for admin interface
Provides REST API endpoints that match the frontend expectations
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...database import get_db
from ...timezone_service import TimezoneService
from ...security import get_current_admin_user
from ... import models

router = APIRouter()


class TimezoneSettingsRequest(BaseModel):
    timezone: str


@router.get("/settings")
def get_timezone_settings(
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


@router.get("/timezones")
def get_available_timezones(
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get list of available timezones"""
    timezone_service = TimezoneService(db)
    timezones = timezone_service.get_available_timezones()
    
    return timezones


@router.post("/settings")
def update_timezone_settings(
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