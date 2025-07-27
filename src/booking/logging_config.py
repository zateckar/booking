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
                from .database import SessionLocal
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
            from .database import SessionLocal
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
    db_handler.setLevel(logging.DEBUG)  # Start with DEBUG, will be updated by stored config
    
    # Create console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # Start with DEBUG, will be updated by stored config
    
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
    
    # Store references to handlers for later level updates
    root_logger._booking_db_handler = db_handler
    root_logger._booking_console_handler = console_handler
    
    # Configure specific loggers with initial levels (will be overridden by stored config)
    loggers_config = {
        'booking': logging.INFO,
        'booking.scheduler': logging.INFO,
        'booking.email_service': logging.INFO,
        'booking.routers': logging.INFO,
        'booking.auth': logging.INFO,
        'booking.database': logging.INFO,
        'booking.services': logging.INFO,
        'uvicorn': logging.WARNING,
        'sqlalchemy.engine': logging.WARNING,
    }
    
    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
    
    return db_handler


def apply_stored_log_configuration():
    """Apply log configuration stored in the database"""
    try:
        from .database import SessionLocal
        from . import models
        
        db = SessionLocal()
        try:
            # Get backend log level from database
            backend_config = db.query(models.AppConfig).filter(
                models.AppConfig.config_key == "backend_log_level"
            ).first()
            
            if backend_config:
                log_level_name = backend_config.config_value.upper()
                if hasattr(logging, log_level_name):
                    log_level = getattr(logging, log_level_name)
                    
                    # Apply to root logger
                    root_logger = logging.getLogger()
                    root_logger.setLevel(log_level)
                    
                    # Update handler levels as well
                    if hasattr(root_logger, '_booking_db_handler'):
                        root_logger._booking_db_handler.setLevel(log_level)
                    if hasattr(root_logger, '_booking_console_handler'):
                        root_logger._booking_console_handler.setLevel(log_level)
                    
                    # Apply to ALL existing loggers that start with "booking"
                    # This catches any logger created with logging.getLogger(__name__) or get_logger()
                    logger_dict = logging.getLogger().manager.loggerDict
                    updated_loggers = []
                    
                    for logger_name, logger_obj in logger_dict.items():
                        if logger_name.startswith('booking'):
                            if isinstance(logger_obj, logging.Logger):
                                logger_obj.setLevel(log_level)
                                updated_loggers.append(logger_name)
                            elif hasattr(logger_obj, 'logger'):
                                # Handle PlaceHolder objects
                                logger_obj.logger.setLevel(log_level)
                                updated_loggers.append(logger_name)
                    
                    # Also apply to specific known booking loggers to ensure they exist
                    booking_loggers = [
                        "booking", "booking.database", "booking.services", "booking.routers",
                        "booking.scheduler", "booking.email_service", "booking.auth",
                        "booking.logging_config", "booking.oidc", "booking.security",
                        "booking.timezone_service", "booking.claims_service", "booking.dynamic_reports_service",
                        "booking.migrations", "booking.migrations.manager", "booking.migrations.discovery",
                        "booking.migrations.runner", "booking.migrations.schema_version", "booking.migrations.base",
                        "booking.routers.admin", "booking.routers.admin.logs", "booking.routers.admin.users",
                        "booking.routers.admin.bookings", "booking.routers.admin.parking_lots", "booking.routers.admin.parking_spaces",
                        "booking.routers.admin.oidc", "booking.routers.admin.oidc_claims", "booking.routers.admin.claims_mapping",
                        "booking.routers.admin.email_settings", "booking.routers.admin.timezone_settings",
                        "booking.routers.admin.styling_settings", "booking.routers.admin.dynamic_reports",
                        "booking.routers.admin.migrations", "booking.routers.admin.backup_settings",
                        "booking.routers.users", "booking.routers.bookings", "booking.routers.auth", "booking.routers.parking_lots",
                        "booking.backup_service", "booking.main"
                    ]
                    
                    for logger_name in booking_loggers:
                        specific_logger = logging.getLogger(logger_name)
                        specific_logger.setLevel(log_level)
                        if logger_name not in updated_loggers:
                            updated_loggers.append(logger_name)
                    
                    # Log the configuration application
                    logger = logging.getLogger("booking.logging_config")
                    logger.info(f"Applied stored backend log level: {log_level_name} to {len(updated_loggers)} loggers and handlers: {', '.join(sorted(updated_loggers))}")
        finally:
            db.close()
    except Exception as e:
        # Don't let logging configuration errors prevent app startup
        # Use basic print since logging might not be fully configured yet
        print(f"Warning: Could not apply stored log configuration: {e}")


def apply_log_level_change(log_level_name: str):
    """Apply a log level change immediately to all loggers and handlers"""
    if hasattr(logging, log_level_name):
        log_level = getattr(logging, log_level_name)
        
        # Apply to root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Update handler levels as well
        if hasattr(root_logger, '_booking_db_handler'):
            root_logger._booking_db_handler.setLevel(log_level)
        if hasattr(root_logger, '_booking_console_handler'):
            root_logger._booking_console_handler.setLevel(log_level)
        
        # Apply to ALL existing loggers that start with "booking"
        # This catches any logger created with logging.getLogger(__name__) or get_logger()
        logger_dict = logging.getLogger().manager.loggerDict
        updated_loggers = []
        
        for logger_name, logger_obj in logger_dict.items():
            if logger_name.startswith('booking'):
                if isinstance(logger_obj, logging.Logger):
                    logger_obj.setLevel(log_level)
                    updated_loggers.append(logger_name)
                elif hasattr(logger_obj, 'logger'):
                    # Handle PlaceHolder objects
                    logger_obj.logger.setLevel(log_level)
                    updated_loggers.append(logger_name)
        
        # Also apply to specific known booking loggers to ensure they exist
        booking_loggers = [
            "booking", "booking.database", "booking.services", "booking.routers",
            "booking.scheduler", "booking.email_service", "booking.auth",
            "booking.logging_config", "booking.oidc", "booking.security",
            "booking.timezone_service", "booking.claims_service", "booking.dynamic_reports_service",
            "booking.migrations", "booking.migrations.manager", "booking.migrations.discovery",
            "booking.migrations.runner", "booking.migrations.schema_version", "booking.migrations.base",
            "booking.routers.admin", "booking.routers.admin.logs", "booking.routers.admin.users",
            "booking.routers.admin.bookings", "booking.routers.admin.parking_lots", "booking.routers.admin.parking_spaces",
            "booking.routers.admin.oidc", "booking.routers.admin.oidc_claims", "booking.routers.admin.claims_mapping",
            "booking.routers.admin.email_settings", "booking.routers.admin.timezone_settings",
            "booking.routers.admin.styling_settings", "booking.routers.admin.dynamic_reports",
            "booking.routers.admin.migrations", "booking.routers.admin.backup_settings",
            "booking.routers.users", "booking.routers.bookings", "booking.routers.auth", "booking.routers.parking_lots",
            "booking.backup_service", "booking.main"
        ]
        
        for logger_name in booking_loggers:
            specific_logger = logging.getLogger(logger_name)
            specific_logger.setLevel(log_level)
            if logger_name not in updated_loggers:
                updated_loggers.append(logger_name)
        
        # Log the successful update
        config_logger = logging.getLogger("booking.logging_config")
        config_logger.info(f"Applied log level {log_level_name} to {len(updated_loggers)} loggers: {', '.join(sorted(updated_loggers))}")


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
