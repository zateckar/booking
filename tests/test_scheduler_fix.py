#!/usr/bin/env python3
"""
Test script to verify the EmailSettings timezone fix
"""

import sys
import os
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_email_settings_timezone():
    """Test that EmailSettings has timezone attribute"""
    
    try:
        from booking.models import EmailSettings
        from booking.database import SessionLocal
        
        print("Testing EmailSettings timezone attribute...")
        
        # Test with database session
        db = SessionLocal()
        try:
            # Try to query EmailSettings
            settings = db.query(EmailSettings).first()
            
            if settings is None:
                # No settings exist, create one for testing
                print("No EmailSettings found, creating test entry...")
                settings = EmailSettings(
                    reports_enabled=False,
                    report_schedule_hour=9,
                    report_frequency="daily",
                    timezone="UTC"
                )
                db.add(settings)
                db.commit()
                db.refresh(settings)
            
            # Test accessing timezone attribute
            timezone_value = settings.timezone
            print(f"✓ EmailSettings.timezone attribute accessible: {timezone_value}")
            
            # Test the scheduler code path that was failing
            user_timezone = settings.timezone or 'UTC'
            print(f"✓ Timezone fallback logic works: {user_timezone}")
            
            return True
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"✗ Error testing EmailSettings timezone: {e}")
        return False

def test_scheduler_import():
    """Test that scheduler can be imported without errors"""
    
    try:
        print("Testing scheduler import...")
        from booking.scheduler import ReportScheduler
        
        # Create scheduler instance
        scheduler = ReportScheduler()
        print("✓ Scheduler imported and instantiated successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Error importing scheduler: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("EmailSettings Timezone Fix Test")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test EmailSettings timezone attribute
    test1_success = test_email_settings_timezone()
    print()
    
    # Test scheduler import
    test2_success = test_scheduler_import()
    print()
    
    overall_success = test1_success and test2_success
    
    if overall_success:
        print("✓ All tests passed!")
        print()
        print("The EmailSettings timezone attribute error has been fixed.")
        print("The scheduler should now work without the 'timezone' attribute error.")
    else:
        print("✗ Some tests failed!")
        print()
        print("There may still be issues with the EmailSettings timezone attribute.")
        print("Please check the error messages above.")
    
    print("=" * 60)
    return 0 if overall_success else 1

if __name__ == "__main__":
    exit(main())
