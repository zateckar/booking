#!/usr/bin/env python3
"""
Manual test script for the email scheduler
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
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def test_scheduler():
    """Test the scheduler functionality"""
    print("=== Email Scheduler Test ===")
    
    # Check current settings
    db = SessionLocal()
    try:
        settings = db.query(models.EmailSettings).first()
        if not settings:
            print("❌ No email settings found")
            return
        
        print(f"📧 Email Settings:")
        print(f"   Reports enabled: {settings.reports_enabled}")
        print(f"   Recipients: {settings.report_recipients}")
        print(f"   Schedule hour: {settings.report_schedule_hour}")
        print(f"   Frequency: {settings.report_frequency}")
        print(f"   Timezone: {settings.timezone}")
        print(f"   Last sent: {settings.last_report_sent}")
        
        if not settings.reports_enabled:
            print("❌ Reports are disabled")
            return
        
        # Test manual email sending
        print("\n🧪 Testing manual email sending...")
        email_service = EmailService(db)
        success = email_service.send_booking_report(force_send=True)
        print(f"   Manual send result: {'✅ Success' if success else '❌ Failed'}")
        
        # Test scheduler logic
        print("\n⏰ Testing scheduler logic...")
        scheduler = ReportScheduler()
        
        now_utc = datetime.now(timezone.utc)
        from booking.timezone_service import TimezoneService
        timezone_service = TimezoneService(db)
        user_timezone = settings.timezone or 'UTC'
        now_local = timezone_service.convert_utc_to_local(now_utc, user_timezone)
        
        print(f"   Current UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Current local: {now_local.strftime('%Y-%m-%d %H:%M:%S')} {user_timezone}")
        print(f"   Current hour: {now_local.hour}")
        print(f"   Scheduled hour: {settings.report_schedule_hour}")
        
        hour_matches = now_local.hour == settings.report_schedule_hour
        should_send = scheduler._should_send_report(settings, now_utc, now_local)
        
        print(f"   Hour matches: {'✅' if hour_matches else '❌'}")
        print(f"   Should send: {'✅' if should_send else '❌'}")
        
        if hour_matches and should_send:
            print("   🎯 Scheduler would send report now!")
        else:
            print("   ⏳ Scheduler would not send report now")
        
        # Test scheduler run (brief)
        print("\n🔄 Testing scheduler run...")
        await scheduler.start()
        print(f"   Scheduler started: {'✅' if scheduler.running else '❌'}")
        
        # Let it run for a few seconds to see if it processes
        await asyncio.sleep(3)
        
        await scheduler.stop()
        print(f"   Scheduler stopped: {'✅' if not scheduler.running else '❌'}")
        
    finally:
        db.close()


async def force_send_report():
    """Force send a report regardless of schedule"""
    print("=== Force Send Report ===")
    
    db = SessionLocal()
    try:
        email_service = EmailService(db)
        print("📤 Sending report...")
        success = email_service.send_booking_report(force_send=True)
        print(f"Result: {'✅ Success' if success else '❌ Failed'}")
        
        if success:
            # Update the database to reflect the send
            settings = db.query(models.EmailSettings).first()
            if settings:
                settings.last_report_sent = datetime.now(timezone.utc)
                db.commit()
                print("✅ Database updated with send time")
        
    finally:
        db.close()


async def reset_last_sent():
    """Reset the last_report_sent to allow immediate testing"""
    print("=== Reset Last Sent Time ===")
    
    db = SessionLocal()
    try:
        settings = db.query(models.EmailSettings).first()
        if settings:
            old_time = settings.last_report_sent
            settings.last_report_sent = datetime.now(timezone.utc) - timedelta(days=1)
            db.commit()
            print(f"✅ Reset last_report_sent from {old_time} to {settings.last_report_sent}")
        else:
            print("❌ No email settings found")
    finally:
        db.close()


async def main():
    """Main test function"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "force":
            await force_send_report()
        elif command == "reset":
            await reset_last_sent()
        elif command == "test":
            await test_scheduler()
        else:
            print("Usage: python test_scheduler_manual.py [test|force|reset]")
    else:
        await test_scheduler()


if __name__ == "__main__":
    asyncio.run(main())