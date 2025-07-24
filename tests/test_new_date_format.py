#!/usr/bin/env python3
"""
Test script to demonstrate the new DD-MM-YYYY date format
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

def test_new_date_format():
    """Test the new DD-MM-YYYY date format"""
    print("Testing new DD-MM-YYYY date format...")
    
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        # Set timezone to Europe/Prague
        settings = EmailSettings(
            timezone="Europe/Prague",
            sendgrid_api_key="test_key",
            from_email="test@example.com"
        )
        db.add(settings)
        db.commit()
        
        # Test with a specific date: July 21, 2025 at 10:00 UTC
        utc_time = datetime(2025, 7, 21, 8, 0, 0, tzinfo=timezone.utc)  # 8:00 UTC = 10:00 Prague time
        
        timezone_service = TimezoneService(db)
        email_service = EmailService(db)
        
        # Test timezone service formatting
        formatted_datetime = timezone_service.format_datetime_local(utc_time)
        formatted_date = timezone_service.format_date_local(utc_time)
        formatted_time = timezone_service.format_time_local(utc_time)
        
        print(f"✓ Timezone service datetime: {formatted_datetime}")
        print(f"✓ Timezone service date only: {formatted_date}")
        print(f"✓ Timezone service time only: {formatted_time}")
        
        # Test email service formatting
        email_formatted = email_service._format_datetime_in_timezone(utc_time)
        print(f"✓ Email service datetime: {email_formatted}")
        
        # Verify the format is correct
        expected_datetime = "21-07-2025 10:00"
        expected_date = "21-07-2025"
        expected_time = "10:00"
        
        assert formatted_datetime == expected_datetime, f"Expected '{expected_datetime}', got '{formatted_datetime}'"
        assert formatted_date == expected_date, f"Expected '{expected_date}', got '{formatted_date}'"
        assert formatted_time == expected_time, f"Expected '{expected_time}', got '{formatted_time}'"
        assert email_formatted == expected_datetime, f"Expected '{expected_datetime}', got '{email_formatted}'"
        
        print("\n✅ All date format tests passed!")
        print(f"✓ Format is DD-MM-YYYY HH:MM (24h) without timezone designator")
        print(f"✓ Example: {formatted_datetime}")
        
        return True

if __name__ == "__main__":
    success = test_new_date_format()
    sys.exit(0 if success else 1)