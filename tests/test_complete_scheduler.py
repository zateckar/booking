#!/usr/bin/env python3
"""
Complete test of the email scheduler functionality
"""
import sys
import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from booking.database import SessionLocal
from booking import models
from booking.scheduler import ReportScheduler
from booking.email_service import EmailService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_complete_scheduler():
    """Test the complete scheduler functionality"""
    print("=== Complete Scheduler Test ===")
    
    db = SessionLocal()
    try:
        # Get settings
        settings = db.query(models.EmailSettings).first()
        if not settings:
            print("No email settings found")
            return
        
        print(f"Current Settings:")
        print(f"   Reports enabled: {settings.reports_enabled}")
        print(f"   Schedule hour: {settings.report_schedule_hour}")
        print(f"   Timezone: {settings.timezone}")
        print(f"   Last sent: {settings.last_report_sent}")
        
        # Reset last_report_sent to yesterday to allow testing
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        settings.last_report_sent = yesterday
        db.commit()
        print(f"Reset last_report_sent to: {yesterday}")
        
        # Create scheduler
        scheduler = ReportScheduler()
        
        # Test the check logic
        print(f"\nTesting scheduler check logic...")
        await scheduler._check_and_send_reports()
        
        # Check if report was sent by looking at updated last_report_sent
        db.refresh(settings)
        if settings.last_report_sent > yesterday:
            print("Report was sent by scheduler!")
            print(f"   New last_report_sent: {settings.last_report_sent}")
        else:
            print("Report was not sent by scheduler")
            print(f"   last_report_sent unchanged: {settings.last_report_sent}")
        
    finally:
        db.close()


async def test_scheduler_with_different_hours():
    """Test scheduler behavior at different hours"""
    print("\n=== Testing Different Hours ===")
    
    db = SessionLocal()
    try:
        settings = db.query(models.EmailSettings).first()
        if not settings:
            return
        
        original_hour = settings.report_schedule_hour
        
        # Test with current hour
        from booking.timezone_service import TimezoneService
        timezone_service = TimezoneService(db)
        now_utc = datetime.now(timezone.utc)
        now_local = timezone_service.convert_utc_to_local(now_utc, settings.timezone or 'UTC')
        current_hour = now_local.hour
        
        print(f"Current local hour: {current_hour}")
        print(f"Scheduled hour: {original_hour}")
        
        # Set schedule to current hour
        settings.report_schedule_hour = current_hour
        settings.last_report_sent = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
        
        print(f"Set schedule to current hour: {current_hour}")
        
        # Test scheduler
        scheduler = ReportScheduler()
        print("Testing scheduler at current hour...")
        await scheduler._check_and_send_reports()
        
        # Check result
        db.refresh(settings)
        if settings.last_report_sent.date() == now_utc.date():
            print("Report sent at current hour!")
        else:
            print("Report not sent at current hour")
        
        # Restore original hour
        settings.report_schedule_hour = original_hour
        db.commit()
        print(f"Restored original schedule hour: {original_hour}")
        
    finally:
        db.close()


async def main():
    """Main test function"""
    await test_complete_scheduler()
    await test_scheduler_with_different_hours()
    print("\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(main())