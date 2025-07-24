#!/usr/bin/env python3
"""
Test script to verify that the scheduler correctly handles timezone-aware email scheduling
"""
import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from booking.models import Base, EmailSettings
from booking.scheduler import ReportScheduler
from booking.timezone_service import TimezoneService

def test_scheduler_timezone_handling():
    """Test that scheduler correctly handles timezone-aware scheduling"""
    
    # Create in-memory database for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    
    try:
        print("Testing scheduler timezone handling...")
        
        # Test 1: UTC timezone (should work as before)
        print("\nTest 1: UTC timezone scheduling...")
        settings = EmailSettings(
            timezone="UTC",
            reports_enabled=True,
            report_schedule_hour=14,  # 2 PM UTC
            sendgrid_api_key="test_key",
            from_email="test@example.com"
        )
        db.add(settings)
        db.commit()
        
        # Mock current time to be 2 PM UTC
        test_utc_time = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        
        timezone_service = TimezoneService(db)
        local_time = timezone_service.convert_utc_to_local(test_utc_time, "UTC")
        
        print(f"✓ UTC time: {test_utc_time.strftime('%H:%M')} UTC")
        print(f"✓ Local time: {local_time.strftime('%H:%M')} UTC")
        print(f"✓ Schedule hour: {settings.report_schedule_hour}")
        print(f"✓ Should send: {local_time.hour == settings.report_schedule_hour}")
        
        assert local_time.hour == settings.report_schedule_hour, "UTC scheduling should work"
        
        # Test 2: Eastern timezone (UTC-5 in winter)
        print("\nTest 2: US/Eastern timezone scheduling...")
        settings.timezone = "US/Eastern"
        settings.report_schedule_hour = 9  # 9 AM Eastern
        db.commit()
        
        # Test time: 2 PM UTC = 9 AM Eastern (winter time)
        test_utc_time = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
        
        timezone_service.refresh_timezone_cache()
        local_time = timezone_service.convert_utc_to_local(test_utc_time, "US/Eastern")
        
        print(f"✓ UTC time: {test_utc_time.strftime('%H:%M')} UTC")
        print(f"✓ Eastern time: {local_time.strftime('%H:%M')} EST")
        print(f"✓ Schedule hour: {settings.report_schedule_hour}")
        print(f"✓ Should send: {local_time.hour == settings.report_schedule_hour}")
        
        assert local_time.hour == settings.report_schedule_hour, "Eastern timezone scheduling should work"
        
        # Test 3: European timezone (UTC+1/+2)
        print("\nTest 3: Europe/Prague timezone scheduling...")
        settings.timezone = "Europe/Prague"
        settings.report_schedule_hour = 10  # 10 AM Prague time
        db.commit()
        
        # Test time: 9 AM UTC = 10 AM Prague (winter time, UTC+1)
        test_utc_time = datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
        
        timezone_service.refresh_timezone_cache()
        local_time = timezone_service.convert_utc_to_local(test_utc_time, "Europe/Prague")
        
        print(f"✓ UTC time: {test_utc_time.strftime('%H:%M')} UTC")
        print(f"✓ Prague time: {local_time.strftime('%H:%M')} CET")
        print(f"✓ Schedule hour: {settings.report_schedule_hour}")
        print(f"✓ Should send: {local_time.hour == settings.report_schedule_hour}")
        
        assert local_time.hour == settings.report_schedule_hour, "Prague timezone scheduling should work"
        
        # Test 4: Wrong time should not trigger
        print("\nTest 4: Wrong time should not trigger...")
        # Test time: 8 AM UTC = 9 AM Prague (should not match 10 AM schedule)
        test_utc_time = datetime(2025, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
        
        local_time = timezone_service.convert_utc_to_local(test_utc_time, "Europe/Prague")
        
        print(f"✓ UTC time: {test_utc_time.strftime('%H:%M')} UTC")
        print(f"✓ Prague time: {local_time.strftime('%H:%M')} CET")
        print(f"✓ Schedule hour: {settings.report_schedule_hour}")
        print(f"✓ Should send: {local_time.hour == settings.report_schedule_hour}")
        
        assert local_time.hour != settings.report_schedule_hour, "Wrong time should not trigger"
        
        # Test 5: Summer time (DST) handling
        print("\nTest 5: Summer time (DST) handling...")
        # Test time: 8 AM UTC = 10 AM Prague (summer time, UTC+2)
        test_utc_time = datetime(2025, 7, 15, 8, 0, 0, tzinfo=timezone.utc)
        
        local_time = timezone_service.convert_utc_to_local(test_utc_time, "Europe/Prague")
        
        print(f"✓ UTC time: {test_utc_time.strftime('%H:%M')} UTC")
        print(f"✓ Prague time (summer): {local_time.strftime('%H:%M')} CEST")
        print(f"✓ Schedule hour: {settings.report_schedule_hour}")
        print(f"✓ Should send: {local_time.hour == settings.report_schedule_hour}")
        
        assert local_time.hour == settings.report_schedule_hour, "Summer time scheduling should work"
        
        print("\n✅ All scheduler timezone tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_scheduler_timezone_handling()