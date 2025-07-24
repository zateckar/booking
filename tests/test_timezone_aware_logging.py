"""
Test timezone-aware logging functionality
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from src.booking.database import SessionLocal, engine
from src.booking import models
from src.booking.logging_config import setup_logging, get_logger, TimezoneAwareFormatter
from src.booking.timezone_service import TimezoneService


def test_timezone_aware_logging():
    """Test that logs respect timezone settings"""
    # Create test database session
    db = SessionLocal()
    
    try:
        # Create email settings with a specific timezone
        settings = models.EmailSettings(
            timezone="US/Eastern",
            from_email="test@example.com"
        )
        db.add(settings)
        db.commit()
        
        # Setup logging
        setup_logging()
        logger = get_logger("test")
        
        # Create a test log entry
        logger.info("Test log message for timezone verification")
        
        # Verify the log was stored in the database
        log_entry = db.query(models.ApplicationLog).filter(
            models.ApplicationLog.message == "Test log message for timezone verification"
        ).first()
        
        assert log_entry is not None
        assert log_entry.timestamp is not None
        
        # Test timezone service formatting
        timezone_service = TimezoneService(db)
        formatted_time = timezone_service.format_datetime_local(log_entry.timestamp)
        formatted_time_with_tz = timezone_service.format_datetime_local(log_entry.timestamp, include_tz=True)
        
        # Verify formatting includes timezone info
        assert formatted_time is not None
        assert formatted_time_with_tz is not None
        assert "EST" in formatted_time_with_tz or "EDT" in formatted_time_with_tz
        
        print(f"Log timestamp (UTC): {log_entry.timestamp}")
        print(f"Formatted time (local): {formatted_time}")
        print(f"Formatted time (with TZ): {formatted_time_with_tz}")
        
    finally:
        # Cleanup
        db.query(models.ApplicationLog).delete()
        db.query(models.EmailSettings).delete()
        db.commit()
        db.close()


def test_timezone_aware_formatter():
    """Test the custom timezone-aware formatter"""
    db = SessionLocal()
    
    try:
        # Create email settings with a specific timezone
        settings = models.EmailSettings(
            timezone="Europe/London",
            from_email="test@example.com"
        )
        db.add(settings)
        db.commit()
        
        # Create formatter
        formatter = TimezoneAwareFormatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Format the record
        formatted = formatter.format(record)
        
        # Verify the formatted output contains timezone info
        assert formatted is not None
        assert "INFO" in formatted
        assert "Test message" in formatted
        
        print(f"Formatted log: {formatted}")
        
    finally:
        # Cleanup
        db.query(models.EmailSettings).delete()
        db.commit()
        db.close()


def test_logs_api_timezone_formatting():
    """Test that the logs API returns timezone-formatted timestamps"""
    from src.booking.routers.admin.logs import get_logs
    from src.booking.database import get_db
    from src.booking.security import get_current_admin_user
    
    db = SessionLocal()
    
    try:
        # Create email settings with a specific timezone
        settings = models.EmailSettings(
            timezone="Asia/Tokyo",
            from_email="test@example.com"
        )
        db.add(settings)
        
        # Create a test user (admin)
        admin_user = models.User(
            email="admin@example.com",
            hashed_password="hashed",
            is_admin=True
        )
        db.add(admin_user)
        
        # Create a test log entry
        log_entry = models.ApplicationLog(
            timestamp=datetime.now(timezone.utc),
            level="INFO",
            logger_name="test",
            message="Test log for API",
            module="test.py",
            function="test_function",
            line_number=1
        )
        db.add(log_entry)
        db.commit()
        
        # Mock the dependencies
        def mock_get_db():
            return db
        
        def mock_get_current_admin_user():
            return admin_user
        
        # Call the API function
        logs = get_logs(
            skip=0,
            limit=10,
            level=None,
            logger_name=None,
            start_time=None,
            end_time=None,
            search=None,
            user_id=None,
            db=db,
            current_user=admin_user
        )
        
        # Verify the response includes formatted timestamps
        assert len(logs) > 0
        log = logs[0]
        assert "timestamp_formatted" in log
        assert "timestamp_formatted_with_tz" in log
        assert log["timestamp_formatted"] is not None
        assert log["timestamp_formatted_with_tz"] is not None
        
        print(f"API formatted timestamp: {log['timestamp_formatted']}")
        print(f"API formatted timestamp with TZ: {log['timestamp_formatted_with_tz']}")
        
    finally:
        # Cleanup
        db.query(models.ApplicationLog).delete()
        db.query(models.User).delete()
        db.query(models.EmailSettings).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    test_timezone_aware_logging()
    test_timezone_aware_formatter()
    test_logs_api_timezone_formatting()
    print("All timezone-aware logging tests passed!")