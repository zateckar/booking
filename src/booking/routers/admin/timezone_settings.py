from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Union
from pydantic import BaseModel

from ...database import get_db
from ...timezone_service import TimezoneService
from ...security import get_current_admin_user
from ... import models

router = APIRouter()


class TimezoneUpdateRequest(BaseModel):
    timezone: str


@router.get("/timezones")
def get_available_timezones(
    request: Request,
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get list of available timezones"""
    timezone_service = TimezoneService(db)
    timezones = timezone_service.get_available_timezones()
    
    return timezones


@router.get("/current")
def get_current_timezone(
    request: Request,
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get the current system timezone"""
    timezone_service = TimezoneService(db)
    current_tz = timezone_service.get_system_timezone()
    
    return {
        "timezone": current_tz,
        "timezone_display": current_tz.replace('_', ' ')
    }


@router.put("/update")
def update_timezone(
    req: Request,
    request: TimezoneUpdateRequest,
    current_admin_user: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Update the system timezone"""
    try:
        timezone_service = TimezoneService(db)
        
        # Validate timezone
        available_timezones = timezone_service.get_available_timezones()
        available_timezone_values = [tz['value'] for tz in available_timezones]
        if request.timezone not in available_timezone_values:
            raise HTTPException(status_code=400, detail="Invalid timezone")
        
        # Update timezone
        timezone_service.set_system_timezone(request.timezone)
        
        return {
            "message": "Timezone updated successfully",
            "timezone": request.timezone
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
