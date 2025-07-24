"""
Admin routes for viewing application logs
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func

from ... import models, schemas
from ...database import get_db
from ...security import get_current_admin_user
from ...timezone_service import TimezoneService

router = APIRouter()


@router.get("/logs")
def get_logs(
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
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """Get all available log levels"""
    levels = db.query(models.ApplicationLog.level).distinct().all()
    return [level[0] for level in levels if level[0]]


@router.get("/logs/loggers")
def get_logger_names(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
):
    """Get all available logger names"""
    loggers = db.query(models.ApplicationLog.logger_name).distinct().all()
    return [logger[0] for logger in loggers if logger[0]]


@router.get("/logs/stats")
def get_log_stats(
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