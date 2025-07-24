#!/usr/bin/env python3
"""
Monitor the scheduler status and provide diagnostics
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
from booking.scheduler import report_scheduler

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def monitor_scheduler():
    """Monitor scheduler status"""
    print("=== Scheduler Monitor ===")
    
    # Check database settings
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
        print(f"   Timezone: {settings.timezone}")
        print(f"   Last sent: {settings.last_report_sent}")
        
        # Check current time vs schedule
        from booking.timezone_service import TimezoneService
        timezone_service = TimezoneService(db)
        now_utc = datetime.now(timezone.utc)
        now_local = timezone_service.convert_utc_to_local(now_utc, settings.timezone or 'UTC')
        
        print(f"\n⏰ Time Status:")
        print(f"   Current UTC: {now_utc.strftime('%H:%M:%S')}")
        print(f"   Current local: {now_local.strftime('%H:%M:%S')} {settings.timezone}")
        print(f"   Current hour: {now_local.hour}")
        print(f"   Scheduled hour: {settings.report_schedule_hour}")
        
        hour_match = now_local.hour == settings.report_schedule_hour
        print(f"   Hour matches: {'✅' if hour_match else '❌'}")
        
        # Check if report should be sent
        if settings.last_report_sent:
            time_since = now_utc - settings.last_report_sent
            hours_since = time_since.total_seconds() / 3600
            different_day = now_local.date() != timezone_service.convert_utc_to_local(settings.last_report_sent, settings.timezone or 'UTC').date()
            
            print(f"   Hours since last report: {hours_since:.2f}")
            print(f"   Different day: {'✅' if different_day else '❌'}")
            print(f"   Should send: {'✅' if hour_match and different_day and hours_since >= 20 else '❌'}")
        
        # Check scheduler status
        print(f"\n🔄 Scheduler Status:")
        print(f"   Running: {'✅' if report_scheduler.running else '❌'}")
        print(f"   Task: {report_scheduler.task}")
        
        if not report_scheduler.running:
            print("   ⚠️  Scheduler is not running!")
            print("   💡 Try starting the FastAPI application to start the scheduler")
        
    finally:
        db.close()


async def start_standalone_scheduler():
    """Start the scheduler in standalone mode for testing"""
    print("\n=== Starting Standalone Scheduler ===")
    
    try:
        await report_scheduler.start()
        print("✅ Scheduler started")
        
        # Let it run for a few minutes
        print("⏳ Running scheduler for 3 minutes...")
        await asyncio.sleep(180)
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    finally:
        await report_scheduler.stop()
        print("✅ Scheduler stopped")


async def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        await start_standalone_scheduler()
    else:
        await monitor_scheduler()


if __name__ == "__main__":
    asyncio.run(main())