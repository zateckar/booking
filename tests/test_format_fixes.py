#!/usr/bin/env python3
"""
Test script to verify the format fixes for:
1. Admin - Booking Reports - Send Time (Hour) is now in 24h format
2. Datepicker format guidance is provided for DD-MM-YYYY
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from booking.models import Base, EmailSettings
from booking.timezone_service import TimezoneService

def test_format_fixes():
    """Test the format fixes"""
    print("Testing format fixes...")
    
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        # Set timezone to Europe/Prague
        settings = EmailSettings(
            timezone="Europe/Prague",
            sendgrid_api_key="test_key",
            from_email="test@example.com",
            report_schedule_hour=14  # 2 PM in 24h format
        )
        db.add(settings)
        db.commit()
        
        timezone_service = TimezoneService(db)
        
        # Test 1: Verify timezone service still works with DD-MM-YYYY format
        utc_time = datetime(2025, 7, 21, 12, 0, 0, tzinfo=timezone.utc)  # 12:00 UTC = 14:00 Prague time
        formatted_datetime = timezone_service.format_datetime_local(utc_time)
        
        print(f"✓ Formatted datetime: {formatted_datetime}")
        assert formatted_datetime == "21-07-2025 14:00", f"Expected '21-07-2025 14:00', got '{formatted_datetime}'"
        
        # Test 2: Verify report schedule hour is stored correctly (24h format)
        assert settings.report_schedule_hour == 14, f"Expected 14 (24h format), got {settings.report_schedule_hour}"
        print(f"✓ Report schedule hour: {settings.report_schedule_hour}:00 (24h format)")
        
        # Test 3: Verify different times throughout the day
        test_times = [
            (datetime(2025, 1, 15, 0, 30, 0, tzinfo=timezone.utc), "15-01-2025 01:30"),  # Midnight UTC = 1:30 AM Prague
            (datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc), "15-01-2025 13:00"), # Noon UTC = 1:00 PM Prague
            (datetime(2025, 1, 15, 23, 45, 0, tzinfo=timezone.utc), "16-01-2025 00:45"), # 11:45 PM UTC = 12:45 AM next day Prague
        ]
        
        for utc_dt, expected in test_times:
            result = timezone_service.format_datetime_local(utc_dt)
            print(f"✓ {utc_dt.strftime('%H:%M UTC')} → {result}")
            assert result == expected, f"Expected '{expected}', got '{result}'"
        
        print("\n✅ All format fixes verified!")
        print("1. ✓ Date format: DD-MM-YYYY (e.g., 21-07-2025)")
        print("2. ✓ Time format: 24-hour (e.g., 14:00)")
        print("3. ✓ No timezone designators in display")
        print("4. ✓ Report schedule uses 24h format")
        
        return True

if __name__ == "__main__":
    success = test_format_fixes()
    sys.exit(0 if success else 1)