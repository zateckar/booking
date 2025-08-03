"""
Admin routes for viewing application logs and managing log configuration
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func, text
from pydantic import BaseModel

from ... import models, schemas
from ...database import get_db
from ...security import get_current_admin_user
from ...timezone_service import TimezoneService
from ...logging_config import get_logger

logger = get_logger("routers.admin.logs")

class LogConfigUpdate(BaseModel):
    backend_log_level: Optional[str] = None
    frontend_log_level: Optional[str] = None

class LogConfigResponse(BaseModel):
    backend_log_level: str
    frontend_log_level: str

router = APIRouter()


@router.get("/logs")
def get_logs(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None, description="Filter by log level"),
    logger_name: Optional[str] = Query(None, description="Filter by logger name"),
    start_time: Optional[datetime] = Query(None, description="Filter logs after this time"),
    end_time: Optional[datetime] = Query(None, description="Filter logs before this time"),
    search: Optional[str] = Query(None, description="Search in log messages"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """Get application logs with filtering options and timezone-aware formatting"""
    
    query = db.query(models.ApplicationLog)
    
    # Apply filters
    filters = []
    
    if level:
        filters.append(models.ApplicationLog.level == level.upper())
    
    if logger_name:
        filters.append(models.ApplicationLog.logger_name.ilike(f"%{logger_name}%"))
    
    if start_time:
        # Ensure timezone awareness
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        filters.append(models.ApplicationLog.timestamp >= start_time)
    
    if end_time:
        # Ensure timezone awareness
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        filters.append(models.ApplicationLog.timestamp <= end_time)
    
    if search:
        filters.append(models.ApplicationLog.message.ilike(f"%{search}%"))
    
    if user_id:
        filters.append(models.ApplicationLog.user_id == user_id)
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Order by timestamp descending (newest first)
    query = query.order_by(desc(models.ApplicationLog.timestamp))
    
    # Apply pagination
    logs = query.offset(skip).limit(limit).all()
    
    # Format timestamps according to timezone settings
    timezone_service = TimezoneService(db)
    
    formatted_logs = []
    for log in logs:
        log_dict = {
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "timestamp_formatted": timezone_service.format_datetime_local(log.timestamp) if log.timestamp else None,
            "timestamp_formatted_with_tz": timezone_service.format_datetime_local(log.timestamp, include_tz=True) if log.timestamp else None,
            "level": log.level,
            "logger_name": log.logger_name,
            "message": log.message,
            "module": log.module,
            "function": log.function,
            "line_number": log.line_number,
            "user_id": log.user_id,
            "request_id": log.request_id,
            "extra_data": log.extra_data,
            "user": {"id": log.user.id, "email": log.user.email} if log.user else None
        }
        formatted_logs.append(log_dict)
    
    return formatted_logs


@router.get("/logs/levels")
def get_log_levels(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """Get all available log levels"""
    levels = db.query(models.ApplicationLog.level).distinct().all()
    return [level[0] for level in levels if level[0]]


@router.get("/logs/loggers")
def get_logger_names(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """Get all available logger names"""
    loggers = db.query(models.ApplicationLog.logger_name).distinct().all()
    return [logger[0] for logger in loggers if logger[0]]


@router.get("/logs/stats")
def get_log_stats(
    request: Request,
    hours: int = Query(24, ge=1, le=168, description="Number of hours to analyze"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """Get log statistics for the specified time period"""
    
    start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    # Get total count by level
    level_counts = (
        db.query(models.ApplicationLog.level, func.count(models.ApplicationLog.id))
        .filter(models.ApplicationLog.timestamp >= start_time)
        .group_by(models.ApplicationLog.level)
        .all()
    )
    
    # Get total count by logger
    logger_counts = (
        db.query(models.ApplicationLog.logger_name, func.count(models.ApplicationLog.id))
        .filter(models.ApplicationLog.timestamp >= start_time)
        .group_by(models.ApplicationLog.logger_name)
        .order_by(desc(func.count(models.ApplicationLog.id)))
        .limit(10)
        .all()
    )
    
    # Get recent error count
    error_count = (
        db.query(models.ApplicationLog)
        .filter(
            and_(
                models.ApplicationLog.timestamp >= start_time,
                models.ApplicationLog.level.in_(['ERROR', 'CRITICAL'])
            )
        )
        .count()
    )
    
    return {
        "time_period_hours": hours,
        "level_counts": {level: count for level, count in level_counts},
        "top_loggers": [{"name": name, "count": count} for name, count in logger_counts],
        "error_count": error_count,
        "total_logs": sum(count for _, count in level_counts)
    }


@router.delete("/logs/cleanup")
def cleanup_old_logs(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Delete logs older than this many days"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """Delete logs older than specified number of days"""
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
    
    deleted_count = (
        db.query(models.ApplicationLog)
        .filter(models.ApplicationLog.timestamp < cutoff_time)
        .delete()
    )
    
    db.commit()
    
    return {
        "deleted_count": deleted_count,
        "cutoff_date": cutoff_time.isoformat()
    }


@router.post("/logs/vacuum")
def vacuum_database(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """Vacuum the database to reclaim space"""
    try:
        db.execute(text("VACUUM"))
        db.commit()
        return {"message": "Database vacuumed successfully"}
    except Exception as e:
        logger.error(f"Error vacuuming database: {e}")
        raise HTTPException(status_code=500, detail="Error vacuuming database")


def _get_log_config(db: Session) -> LogConfigResponse:
    """Helper to get current logging configuration"""
    
    # Get backend log level from AppConfig
    backend_level_config = db.query(models.AppConfig).filter(
        models.AppConfig.config_key == "backend_log_level"
    ).first()
    
    frontend_level_config = db.query(models.AppConfig).filter(
        models.AppConfig.config_key == "frontend_log_level"
    ).first()
    
    # Default to INFO level if not configured
    backend_level = backend_level_config.config_value if backend_level_config else "INFO"
    frontend_level = frontend_level_config.config_value if frontend_level_config else "INFO"
    
    return LogConfigResponse(
        backend_log_level=backend_level,
        frontend_log_level=frontend_level
    )


@router.get("/logs/config", response_model=LogConfigResponse)
def get_log_config(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """Get current logging configuration"""
    return _get_log_config(db)


@router.put("/logs/config", response_model=LogConfigResponse)
def update_log_config(
    request: Request,
    config_update: LogConfigUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """Update logging configuration"""
    
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    if config_update.backend_log_level:
        if config_update.backend_log_level.upper() not in valid_levels:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid backend log level. Must be one of: {', '.join(valid_levels)}"
            )
        
        # Update or create backend log level config
        backend_config = db.query(models.AppConfig).filter(
            models.AppConfig.config_key == "backend_log_level"
        ).first()
        
        if backend_config:
            backend_config.config_value = config_update.backend_log_level.upper()
        else:
            backend_config = models.AppConfig(
                config_key="backend_log_level",
                config_value=config_update.backend_log_level.upper(),
                description="Backend Python logger level"
            )
            db.add(backend_config)
        
        # Apply the log level change immediately to all loggers and handlers
        from ...logging_config import apply_log_level_change
        apply_log_level_change(config_update.backend_log_level.upper())
        
        logger.info(f"Backend log level updated to {config_update.backend_log_level.upper()}")
    
    if config_update.frontend_log_level:
        if config_update.frontend_log_level.upper() not in valid_levels:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid frontend log level. Must be one of: {', '.join(valid_levels)}"
            )
        
        # Update or create frontend log level config
        frontend_config = db.query(models.AppConfig).filter(
            models.AppConfig.config_key == "frontend_log_level"
        ).first()
        
        if frontend_config:
            frontend_config.config_value = config_update.frontend_log_level.upper()
        else:
            frontend_config = models.AppConfig(
                config_key="frontend_log_level",
                config_value=config_update.frontend_log_level.upper(),
                description="Frontend console logging level"
            )
            db.add(frontend_config)
        
        logger.info(f"Frontend log level updated to {config_update.frontend_log_level.upper()}")
    
    db.commit()
    
    # Return updated configuration
    return _get_log_config(db)
