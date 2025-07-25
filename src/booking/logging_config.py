"""
Logging configuration for the booking application
"""
import logging
import json
import traceback
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .database import SessionLocal
from . import models


class TimezoneAwareFormatter(logging.Formatter):
    """Custom formatter that formats timestamps according to application timezone settings"""
    
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self._shutdown_detected = False
        self._cached_timezone = None
    
    def formatTime(self, record, datefmt=None):
        """Format the timestamp using the application's timezone settings"""
        try:
            # Create a datetime from the record timestamp
            dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
            
            # If shutdown was detected previously, skip database access
            if self._shutdown_detected:
                return dt.strftime("%d-%m-%Y %H:%M:%S UTC")
            
            # Import here to avoid circular imports
            from .timezone_service import TimezoneService
            
            # Try to get timezone service with a temporary database session
            db = None
            try:
                db = SessionLocal()
                timezone_service = TimezoneService(db)
                # Format with timezone info for console logs
                formatted_time = timezone_service.format_datetime_local(
                    dt, 
                    format_str="%d-%m-%Y %H:%M:%S",
                    include_tz=True
                )
                return formatted_time
            except (SQLAlchemyError, OSError, ConnectionError) as e:
                # These exceptions indicate database/connection issues during shutdown
                self._shutdown_detected = True
                return dt.strftime("%d-%m-%Y %H:%M:%S UTC")
            except Exception:
                # Other exceptions - still try database next time
                return dt.strftime("%d-%m-%Y %H:%M:%S UTC")
            finally:
                if db:
                    try:
                        db.close()
                    except Exception:
                        # Ignore cleanup errors during shutdown
                        pass
                
        except Exception:
            # Ultimate fallback to standard formatting
            return super().formatTime(record, datefmt)


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that stores logs in the database"""
    
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self.request_id = None
        self.user_id = None
        self._shutdown_detected = False
    
    def set_context(self, request_id: Optional[str] = None, user_id: Optional[int] = None):
        """Set context information for logs"""
        self.request_id = request_id
        self.user_id = user_id
    
    def emit(self, record):
        """Store log record in database"""
        # Skip database logging if shutdown was detected
        if self._shutdown_detected:
            return
            
        db = None
        try:
            db = SessionLocal()
            try:
                # Extract extra data if present
                extra_data = {}
                if hasattr(record, 'extra_data'):
                    extra_data.update(record.extra_data)
                
                # Add exception info if present
                if record.exc_info:
                    extra_data['exception'] = {
                        'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                        'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                        'traceback': traceback.format_exception(*record.exc_info)
                    }
                
                log_entry = models.ApplicationLog(
                    timestamp=datetime.now(timezone.utc),
                    level=record.levelname,
                    logger_name=record.name,
                    message=record.getMessage(),
                    module=record.module if hasattr(record, 'module') else record.filename,
                    function=record.funcName,
                    line_number=record.lineno,
                    user_id=getattr(record, 'user_id', self.user_id),
                    request_id=getattr(record, 'request_id', self.request_id),
                    extra_data=json.dumps(extra_data) if extra_data else None
                )
                
                db.add(log_entry)
                db.commit()
            finally:
                if db:
                    try:
                        db.close()
                    except Exception:
                        # Ignore cleanup errors during shutdown
                        pass
        except (SQLAlchemyError, OSError, ConnectionError):
            # Database/connection errors during shutdown - stop trying to log to database
            self._shutdown_detected = True
        except Exception:
            # Catch any other exceptions to prevent logging from breaking the app
            pass


def setup_logging():
    """Configure application logging"""
    # Create database handler
    db_handler = DatabaseLogHandler()
    db_handler.setLevel(logging.INFO)
    
    # Create console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Create timezone-aware formatter
    formatter = TimezoneAwareFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(db_handler)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    loggers_config = {
        'booking': logging.INFO,
        'booking.scheduler': logging.INFO,
        'booking.email_service': logging.INFO,
        'booking.routers': logging.INFO,
        'booking.auth': logging.INFO,
        'uvicorn': logging.WARNING,
        'sqlalchemy.engine': logging.WARNING,
    }
    
    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
    
    return db_handler


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(f"booking.{name}")


def log_with_context(logger: logging.Logger, level: int, message: str, 
                    user_id: Optional[int] = None, request_id: Optional[str] = None, 
                    extra_data: Optional[dict] = None):
    """Log a message with additional context"""
    extra = {}
    if user_id:
        extra['user_id'] = user_id
    if request_id:
        extra['request_id'] = request_id
    if extra_data:
        extra['extra_data'] = extra_data
    
    logger.log(level, message, extra=extra)
