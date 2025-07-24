"""
Simple test for timezone-aware logging functionality
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from src.booking.database import SessionLocal
from src.booking import models
from src.booking.logging_config import setup_logging, get_logger
from src.booking.timezone_service import TimezoneService


def test_basic_timezone_logging():
    """Test basic timezone-aware logging functionality"""
    print("Testing timezone-aware logging...")
    
    # Create test database session
    db = SessionLocal()
    
    try:
        # Clean up any existing test data
        db.query(models.ApplicationLog).filter(
            models.ApplicationLog.message.like("Test timezone log%")
        ).delete()
        db.query(models.EmailSettings).delete()
        db.commit()
        
        # Create email settings with a specific timezone
        settings = models.EmailSettings(
            timezone="US/Pacific",
            from_email="test@example.com"
        )
        db.add(settings)
        db.commit()
        
        # Setup logging
        setup_logging()
        logger = get_logger("timezone_test")
        
        # Create a test log entry
        test_message = "Test timezone log message"
        logger.info(test_message)
        
        # Give it a moment to process
        import time
        time.sleep(0.1)
        
        # Verify the log was stored in the database
        log_entry = db.query(models.ApplicationLog).filter(
            models.ApplicationLog.message == test_message
        ).first()
        
        if log_entry:
            print(f"✓ Log entry created successfully")
            print(f"  UTC timestamp: {log_entry.timestamp}")
            
            # Test timezone service formatting
            timezone_service = TimezoneService(db)
            formatted_time = timezone_service.format_datetime_local(log_entry.timestamp)
            formatted_time_with_tz = timezone_service.format_datetime_local(log_entry.timestamp, include_tz=True)
            
            print(f"  Formatted (local): {formatted_time}")
            print(f"  Formatted (with TZ): {formatted_time_with_tz}")
            
            # Verify formatting
            if formatted_time and formatted_time_with_tz:
                print("✓ Timezone formatting working correctly")
                if "PST" in formatted_time_with_tz or "PDT" in formatted_time_with_tz:
                    print("✓ Pacific timezone detected in formatted output")
                else:
                    print(f"! Expected PST/PDT in output, got: {formatted_time_with_tz}")
            else:
                print("✗ Timezone formatting failed")
        else:
            print("✗ Log entry not found in database")
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        try:
            db.query(models.ApplicationLog).filter(
                models.ApplicationLog.message.like("Test timezone log%")
            ).delete()
            db.query(models.EmailSettings).delete()
            db.commit()
        except:
            pass
        db.close()


def test_different_timezones():
    """Test logging with different timezone settings"""
    print("\nTesting different timezones...")
    
    timezones_to_test = [
        "UTC",
        "US/Eastern", 
        "Europe/London",
        "Asia/Tokyo"
    ]
    
    for tz in timezones_to_test:
        print(f"\nTesting timezone: {tz}")
        
        db = SessionLocal()
        try:
            # Clean up
            db.query(models.EmailSettings).delete()
            db.commit()
            
            # Create settings with this timezone
            settings = models.EmailSettings(
                timezone=tz,
                from_email="test@example.com"
            )
            db.add(settings)
            db.commit()
            
            # Test timezone service
            timezone_service = TimezoneService(db)
            test_time = datetime.now(timezone.utc)
            
            formatted = timezone_service.format_datetime_local(test_time, include_tz=True)
            print(f"  Current time in {tz}: {formatted}")
            
        except Exception as e:
            print(f"  ✗ Error testing {tz}: {e}")
        finally:
            db.close()


if __name__ == "__main__":
    test_basic_timezone_logging()
    test_different_timezones()
    print("\nTimezone-aware logging tests completed!")