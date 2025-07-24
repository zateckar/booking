#!/usr/bin/env python3
"""
Test script for timezone API functionality
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from booking.models import Base, EmailSettings
from booking.timezone_service import TimezoneService
from booking.routers.admin.timezone_settings import get_available_timezones, get_current_timezone

def test_timezone_api():
    """Test timezone API endpoints"""
    print("Testing timezone API endpoints...")
    
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        # Test 1: Get available timezones
        print("Test 1: Getting available timezones...")
        try:
            result = get_available_timezones(db)
            print(f"✓ Available timezones endpoint works")
            print(f"  - Found {len(result['timezones'])} timezones")
            print(f"  - Current timezone: {result['current_timezone']}")
        except Exception as e:
            print(f"✗ Available timezones endpoint failed: {e}")
            return False
        
        # Test 2: Get current timezone
        print("\nTest 2: Getting current timezone...")
        try:
            result = get_current_timezone(db)
            print(f"✓ Current timezone endpoint works")
            print(f"  - Timezone: {result['timezone']}")
            print(f"  - Display: {result['timezone_display']}")
        except Exception as e:
            print(f"✗ Current timezone endpoint failed: {e}")
            return False
        
        # Test 3: Set timezone and verify
        print("\nTest 3: Setting timezone and verifying...")
        try:
            settings = EmailSettings(timezone="US/Pacific")
            db.add(settings)
            db.commit()
            
            result = get_current_timezone(db)
            if result['timezone'] == 'US/Pacific':
                print(f"✓ Timezone setting works correctly")
            else:
                print(f"✗ Timezone setting failed: expected US/Pacific, got {result['timezone']}")
                return False
        except Exception as e:
            print(f"✗ Timezone setting test failed: {e}")
            return False
    
    print("\n✅ All timezone API tests passed!")
    return True

if __name__ == "__main__":
    success = test_timezone_api()
    sys.exit(0 if success else 1)