#!/usr/bin/env python3
"""
Test script to verify timezone functionality
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from booking.models import Base, EmailSettings
from booking.timezone_service import TimezoneService
from booking.email_service import EmailService

def test_timezone_functionality():
    """Test the timezone functionality"""
    print("Testing timezone functionality...")
    
    # Create in-memory database for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Test 1: Default timezone should be UTC
        timezone_service = TimezoneService(db)
        default_tz = timezone_service.get_system_timezone()
        print(f"✓ Default timezone: {default_tz}")
        assert default_tz == 'UTC', f"Expected UTC, got {default_tz}"
        
        # Test 2: Create email settings with timezone
        settings = EmailSettings(
            sendgrid_api_key="test_key",
            from_email="test@example.com",
            from_name="Test System",
            timezone="US/Eastern"
        )
        db.add(settings)
        db.commit()
        
        # Test 3: Timezone service should return configured timezone
        timezone_service.refresh_timezone_cache()
        configured_tz = timezone_service.get_system_timezone()
        print(f"✓ Configured timezone: {configured_tz}")
        assert configured_tz == 'US/Eastern', f"Expected US/Eastern, got {configured_tz}"
        
        # Test 4: Test timezone conversion
        utc_time = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        local_time = timezone_service.convert_utc_to_local(utc_time, 'US/Eastern')
        print(f"✓ UTC to Eastern conversion: {utc_time} -> {local_time}")
        
        # Test 5: Test date formatting
        formatted_time = timezone_service.format_datetime_local(utc_time, timezone_name='US/Eastern')
        print(f"✓ Formatted time: {formatted_time}")
        
        # Test 6: Test available timezones
        timezones = timezone_service.get_available_timezones()
        print(f"✓ Available timezones count: {len(timezones)}")
        assert len(timezones) > 0, "Should have available timezones"
        
        # Test 7: Test email service with timezone
        email_service = EmailService(db)
        test_time = datetime(2024, 1, 15, 20, 0, 0, tzinfo=timezone.utc)
        formatted_email_time = email_service._format_datetime_in_timezone(test_time)
        print(f"✓ Email formatted time: {formatted_email_time}")
        
        print("\n✅ All timezone functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    success = test_timezone_functionality()
    sys.exit(0 if success else 1)