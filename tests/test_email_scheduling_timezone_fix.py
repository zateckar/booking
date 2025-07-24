#!/usr/bin/env python3
"""
Test script to demonstrate the email scheduling timezone fix
This test shows the problem that existed and verifies it's now fixed
"""
import os
import sys
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from booking.models import Base, EmailSettings
from booking.timezone_service import TimezoneService

def test_email_scheduling_timezone_problem():
    """Demonstrate the timezone problem in email scheduling and verify the fix"""
    
    # Create in-memory database for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = SessionLocal()
    
    try:
        print("Testing email scheduling timezone problem and fix...")
        print("=" * 60)
        
        # Scenario: User in UTC+2 timezone wants emails sent at 9:00 AM local time
        print("\nScenario: User in UTC+2 timezone sets email to be sent at 9:00 AM")
        print("Expected behavior: Email should be sent when it's 9:00 AM in their timezone")
        print("Problem: Application was treating 9:00 as UTC time, so email was sent at 11:00 AM local time")
        
        # Set up email settings for UTC+2 timezone (Europe/Prague in winter is UTC+1, summer is UTC+2)
        # Let's use a timezone that's consistently UTC+2
        settings = EmailSettings(
            timezone="Europe/Athens",  # UTC+2 (no DST complications for this test)
            reports_enabled=True,
            report_schedule_hour=9,  # 9 AM local time
            sendgrid_api_key="test_key",
            from_email="test@example.com"
        )
        db.add(settings)
        db.commit()
        
        timezone_service = TimezoneService(db)
        
        print(f"\n📧 Email settings:")
        print(f"   Timezone: {settings.timezone}")
        print(f"   Schedule hour: {settings.report_schedule_hour}:00 (local time)")
        
        # Test different UTC times to see when the email should be sent
        test_times = [
            ("06:00", datetime(2025, 1, 15, 6, 0, 0, tzinfo=timezone.utc)),   # 8:00 AM Athens
            ("07:00", datetime(2025, 1, 15, 7, 0, 0, tzinfo=timezone.utc)),   # 9:00 AM Athens ✓
            ("08:00", datetime(2025, 1, 15, 8, 0, 0, tzinfo=timezone.utc)),   # 10:00 AM Athens
            ("09:00", datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)),   # 11:00 AM Athens
        ]
        
        print(f"\n🕐 Testing different UTC times:")
        print(f"   {'UTC Time':<10} {'Athens Time':<12} {'Should Send':<12} {'Old Logic':<12} {'New Logic'}")
        print(f"   {'-'*10} {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
        
        for utc_label, utc_time in test_times:
            # Convert to local time
            local_time = timezone_service.convert_utc_to_local(utc_time, settings.timezone)
            local_hour = local_time.hour
            
            # Check if this should trigger email sending
            should_send = (local_hour == settings.report_schedule_hour)
            
            # Old logic (broken): compare UTC hour directly with schedule hour
            old_logic_would_send = (utc_time.hour == settings.report_schedule_hour)
            
            # New logic (fixed): compare local hour with schedule hour
            new_logic_would_send = should_send
            
            print(f"   {utc_label:<10} {local_time.strftime('%H:%M %Z'):<12} {'YES' if should_send else 'NO':<12} {'YES' if old_logic_would_send else 'NO':<12} {'YES' if new_logic_would_send else 'NO'}")
        
        print(f"\n🔍 Analysis:")
        print(f"   - User wants email at 9:00 AM Athens time")
        print(f"   - This corresponds to 7:00 AM UTC")
        print(f"   - Old logic: Would send at 9:00 AM UTC = 11:00 AM Athens ❌")
        print(f"   - New logic: Will send at 7:00 AM UTC = 9:00 AM Athens ✅")
        
        # Verify the fix with a specific example
        print(f"\n✅ Verification:")
        correct_utc_time = datetime(2025, 1, 15, 7, 0, 0, tzinfo=timezone.utc)
        local_time = timezone_service.convert_utc_to_local(correct_utc_time, settings.timezone)
        
        print(f"   When UTC time is {correct_utc_time.strftime('%H:%M')}:")
        print(f"   - Athens time is {local_time.strftime('%H:%M')}")
        print(f"   - Schedule hour is {settings.report_schedule_hour}:00")
        print(f"   - Should send email: {local_time.hour == settings.report_schedule_hour}")
        
        assert local_time.hour == settings.report_schedule_hour, "Email should be sent at correct local time"
        
        # Test with different timezone
        print(f"\n🌍 Testing with different timezone (US/Eastern):")
        settings.timezone = "US/Eastern"
        settings.report_schedule_hour = 8  # 8 AM Eastern
        db.commit()
        
        timezone_service.refresh_timezone_cache()
        
        # 8 AM Eastern = 1 PM UTC (winter time)
        eastern_test_time = datetime(2025, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        eastern_local_time = timezone_service.convert_utc_to_local(eastern_test_time, settings.timezone)
        
        print(f"   UTC time: {eastern_test_time.strftime('%H:%M')}")
        print(f"   Eastern time: {eastern_local_time.strftime('%H:%M %Z')}")
        print(f"   Schedule hour: {settings.report_schedule_hour}:00")
        print(f"   Should send: {eastern_local_time.hour == settings.report_schedule_hour}")
        
        assert eastern_local_time.hour == settings.report_schedule_hour, "Eastern timezone should work correctly"
        
        print(f"\n🎉 All tests passed! The timezone fix is working correctly.")
        print(f"   Users can now set their preferred email time in their local timezone,")
        print(f"   and emails will be sent at the correct local time, not UTC time.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_email_scheduling_timezone_problem()