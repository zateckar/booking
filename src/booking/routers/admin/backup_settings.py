from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime, timezone
import os
import logging

from ...database import get_db
from ...models import BackupSettings
from ...schemas import User
from ...security import get_current_admin_user
from ...backup_service import create_backup_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backup-settings", tags=["admin", "backup"])


@router.get("/")
async def get_backup_settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Get current backup settings"""
    settings = db.query(BackupSettings).first()
    
    if not settings:
        # Return default settings if none exist
        return {
            "enabled": False,
            "storage_account": "",
            "container_name": "",
            "sas_token": "",
            "backup_frequency": "daily",
            "backup_hour": 2,
            "keep_backups": 30,
            "last_backup_time": None,
            "last_backup_status": None,
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


@router.put("/")
async def update_backup_settings(
    request: Request,
    settings_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """Update backup settings"""
    
    settings = db.query(BackupSettings).first()
    
    if not settings:
        settings = BackupSettings()
        db.add(settings)
    
    # Update settings
    settings.enabled = settings_data.get("enabled", False)
    settings.storage_account = settings_data.get("storage_account", "")
    settings.container_name = settings_data.get("container_name", "")
    settings.sas_token = settings_data.get("sas_token", "")
    settings.backup_frequency = settings_data.get("backup_frequency", "daily")
    settings.backup_hour = settings_data.get("backup_hour", 2)
    settings.keep_backups = settings_data.get("keep_backups", 30)
    
    try:
        db.commit()
        logger.info(f"Backup settings updated by user {current_user.email}")
        return {"message": "Backup settings updated successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update backup settings: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update backup settings")


@router.post("/test-connection")
async def test_backup_connection(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """Test connection to Azure Blob Storage"""
    
    settings = db.query(BackupSettings).first()
    
    if not settings or not all([settings.storage_account, settings.container_name, settings.sas_token]):
        raise HTTPException(
            status_code=400, 
            detail="Backup settings not configured. Please set storage account, container name, and SAS token."
        )
    
    try:
        backup_service = create_backup_service(
            storage_account=settings.storage_account,
            container_name=settings.container_name,
            sas_token=settings.sas_token
        )
        
        result = backup_service.test_connection()
        logger.info(f"Backup connection test performed by user {current_user.email}: {result['success']}")
        return result
        
    except Exception as e:
        logger.error(f"Backup connection test failed: {str(e)}")
        return {
            "success": False,
            "error": f"Connection test failed: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.post("/backup-now")
async def backup_now(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, str]:
    """Trigger an immediate backup"""
    
    settings = db.query(BackupSettings).first()
    
    if not settings or not settings.enabled:
        raise HTTPException(status_code=400, detail="Backup is not enabled")
    
    if not all([settings.storage_account, settings.container_name, settings.sas_token]):
        raise HTTPException(
            status_code=400, 
            detail="Backup settings incomplete. Please configure all required fields."
        )
    
    # Check if backup is already running
    if settings.last_backup_status == "running":
        raise HTTPException(status_code=409, detail="Backup is already running")
    
    # Update status to running
    settings.last_backup_status = "running"
    settings.last_backup_error = None
    db.commit()
    
    # Run backup in background
    background_tasks.add_task(
        perform_backup,
        settings.storage_account,
        settings.container_name,
        settings.sas_token,
        current_user.email
    )
    
    logger.info(f"Manual backup initiated by user {current_user.email}")
    return {"message": "Backup started. Check the status in a few moments."}


@router.get("/list-backups")
async def list_backups(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """List existing backups in Azure Blob Storage"""
    
    settings = db.query(BackupSettings).first()
    
    if not settings or not all([settings.storage_account, settings.container_name, settings.sas_token]):
        raise HTTPException(
            status_code=400, 
            detail="Backup settings not configured"
        )
    
    try:
        backup_service = create_backup_service(
            storage_account=settings.storage_account,
            container_name=settings.container_name,
            sas_token=settings.sas_token
        )
        
        result = backup_service.list_backups(limit=limit)
        return result
        
    except Exception as e:
        logger.error(f"Failed to list backups: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to list backups: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def perform_backup(storage_account: str, container_name: str, sas_token: str, user_email: str):
    """Perform the actual backup operation (runs in background)"""
    
    from ...database import SessionLocal
    
    db = SessionLocal()
    try:
        settings = db.query(BackupSettings).first()
        if not settings:
            return
        
        backup_service = create_backup_service(
            storage_account=storage_account,
            container_name=container_name,
            sas_token=sas_token
        )
        
        # Get database file path
        db_path = "./booking.db"  # Adjust path as needed
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found: {db_path}")
        
        # Perform backup
        result = backup_service.upload_database_backup(db_path)
        
        # Update settings with result
        settings.last_backup_time = datetime.now(timezone.utc)
        
        if result["success"]:
            settings.last_backup_status = "success"
            settings.last_backup_error = None
            settings.last_backup_size_mb = result.get("file_size_mb", 0)
            logger.info(f"Backup completed successfully. Size: {result.get('file_size_mb', 0)} MB")
        else:
            settings.last_backup_status = "failed"
            settings.last_backup_error = result.get("error", "Unknown error")
            logger.error(f"Backup failed: {result.get('error', 'Unknown error')}")
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Backup operation failed: {str(e)}")
        # Update status to failed
        settings = db.query(BackupSettings).first()
        if settings:
            settings.last_backup_status = "failed"
            settings.last_backup_error = str(e)
            settings.last_backup_time = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
