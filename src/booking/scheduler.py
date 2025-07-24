"""
Background scheduler for periodic email reports and database backups
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from .database import SessionLocal
from .email_service import EmailService
from . import models
from .backup_service import create_backup_service
from .logging_config import get_logger

logger = get_logger("scheduler")


class ReportScheduler:
    """Background scheduler for sending periodic booking reports and database backups"""
    
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logger.info("Report scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("Report scheduler stopped")
    
    async def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info("Scheduler loop started")
        while self.running:
            try:
                logger.debug("Checking if reports should be sent...")
                await self._check_and_send_reports()
                
                logger.debug("Checking if backups should be performed...")
                await self._check_and_perform_backups()
                
                # Check every 10 minutes instead of every hour for more responsive scheduling
                logger.debug("Sleeping for 10 minutes...")
                await asyncio.sleep(600)  # 10 minutes
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                # Wait 2 minutes before retrying on error
                await asyncio.sleep(120)
    
    async def _check_and_send_reports(self):
        """Check if reports should be sent and send them"""
        db = SessionLocal()
        try:
            await self._check_and_send_static_reports(db)
            await self._check_and_send_dynamic_reports(db)
        except Exception as e:
            logger.error(f"Error checking and sending reports: {str(e)}")
        finally:
            db.close()
    
    async def _check_and_send_static_reports(self, db: Session):
        """Check if static reports should be sent and send them"""
        try:
            settings = db.query(models.EmailSettings).first()
            if not settings:
                logger.debug("No email settings found")
                return
                
            if not settings.reports_enabled:
                logger.debug("Static reports are disabled")
                return
            
            # Import timezone service here to avoid circular imports
            from .timezone_service import TimezoneService
            
            now = datetime.now(timezone.utc)
            timezone_service = TimezoneService(db)
            
            # Get the configured timezone (defaults to UTC if not set)
            user_timezone = settings.timezone or 'UTC'
            
            # Convert current UTC time to user's timezone
            local_now = timezone_service.convert_utc_to_local(now, user_timezone)
            current_local_hour = local_now.hour
            
            logger.debug(f"Static report time check: local={local_now.strftime('%H:%M')} {user_timezone}, scheduled={settings.report_schedule_hour}:00")
            
            # Check if it's time to send report based on schedule in user's timezone
            if current_local_hour != settings.report_schedule_hour:
                logger.debug(f"Not time to send static report (current hour: {current_local_hour}, scheduled: {settings.report_schedule_hour})")
                return
            
            # Check if we should send based on frequency and last sent time
            should_send = self._should_send_report(settings, now, local_now)
            logger.debug(f"Should send static report: {should_send}")
            if not should_send:
                logger.debug("Static report sending skipped based on frequency/timing rules")
                return
            
            logger.info(f"Sending scheduled static report at {local_now.strftime('%H:%M')} {user_timezone}")
            
            # Send the report
            email_service = EmailService(db)
            success = email_service.send_booking_report()
            
            if success:
                logger.info(f"Scheduled static report sent successfully at {local_now.strftime('%H:%M')} {user_timezone}")
            else:
                logger.error("Failed to send scheduled static report")
                
        except Exception as e:
            logger.error(f"Error checking and sending static reports: {str(e)}")
    
    async def _check_and_send_dynamic_reports(self, db: Session):
        """Check if dynamic reports should be sent and send them"""
        try:
            settings = db.query(models.EmailSettings).first()
            if not settings:
                logger.debug("No email settings found")
                return
                
            if not settings.dynamic_reports_enabled:
                logger.debug("Dynamic reports are disabled")
                return
            
            if not settings.dynamic_report_template_id:
                logger.debug("No dynamic report template configured")
                return
            
            # Import timezone service here to avoid circular imports
            from .timezone_service import TimezoneService
            
            now = datetime.now(timezone.utc)
            timezone_service = TimezoneService(db)
            
            # Get the configured timezone (defaults to UTC if not set)
            user_timezone = settings.timezone or 'UTC'
            
            # Convert current UTC time to user's timezone
            local_now = timezone_service.convert_utc_to_local(now, user_timezone)
            current_local_hour = local_now.hour
            
            logger.debug(f"Dynamic report time check: local={local_now.strftime('%H:%M')} {user_timezone}, scheduled={settings.dynamic_report_schedule_hour}:00")
            
            # Check if it's time to send report based on schedule in user's timezone
            if current_local_hour != settings.dynamic_report_schedule_hour:
                logger.debug(f"Not time to send dynamic report (current hour: {current_local_hour}, scheduled: {settings.dynamic_report_schedule_hour})")
                return
            
            # Check if we should send based on frequency and last sent time
            should_send = self._should_send_dynamic_report(settings, now, local_now)
            logger.debug(f"Should send dynamic report: {should_send}")
            if not should_send:
                logger.debug("Dynamic report sending skipped based on frequency/timing rules")
                return
            
            logger.info(f"Sending scheduled dynamic report at {local_now.strftime('%H:%M')} {user_timezone}")
            
            # Send the dynamic report
            from .dynamic_reports_service import DynamicReportsService
            reports_service = DynamicReportsService(db)
            success = reports_service.send_scheduled_dynamic_report()
            
            if success:
                logger.info(f"Scheduled dynamic report sent successfully at {local_now.strftime('%H:%M')} {user_timezone}")
            else:
                logger.error("Failed to send scheduled dynamic report")
                
        except Exception as e:
            logger.error(f"Error checking and sending dynamic reports: {str(e)}")
    
    def _should_send_report(self, settings, now_utc: datetime, now_local: datetime) -> bool:
        """
        Determine if a report should be sent based on frequency and last sent time
        
        Args:
            settings: EmailSettings object
            now_utc: Current UTC datetime
            now_local: Current local datetime
            
        Returns:
            True if report should be sent, False otherwise
        """
        if not settings.last_report_sent:
            # Never sent before, send now
            return True
        
        # Import timezone service here to avoid circular imports
        from .timezone_service import TimezoneService
        from datetime import timedelta
        
        # Convert last sent time to local timezone for comparison
        timezone_service = TimezoneService(SessionLocal())
        user_timezone = settings.timezone or 'UTC'
        last_sent_local = timezone_service.convert_utc_to_local(settings.last_report_sent, user_timezone)
        
        # Check based on frequency
        if settings.report_frequency == "daily":
            # Send if it's a different day or if it's been more than 20 hours
            # (to handle edge cases around DST changes)
            different_day = now_local.date() != last_sent_local.date()
            time_threshold = (now_utc - settings.last_report_sent).total_seconds() >= 72000  # 20 hours
            return different_day and time_threshold
            
        elif settings.report_frequency == "weekly":
            # Send if it's been at least 6 days and it's the same day of week or later
            days_since = (now_utc - settings.last_report_sent).days
            return days_since >= 6
            
        elif settings.report_frequency == "monthly":
            # Send if it's been at least 28 days
            days_since = (now_utc - settings.last_report_sent).days
            return days_since >= 28
        
        # Default to daily behavior
        different_day = now_local.date() != last_sent_local.date()
        time_threshold = (now_utc - settings.last_report_sent).total_seconds() >= 72000  # 20 hours
        return different_day and time_threshold
    
    def _should_send_dynamic_report(self, settings, now_utc: datetime, now_local: datetime) -> bool:
        """
        Determine if a dynamic report should be sent based on frequency and last sent time
        
        Args:
            settings: EmailSettings object
            now_utc: Current UTC datetime
            now_local: Current local datetime
            
        Returns:
            True if dynamic report should be sent, False otherwise
        """
        if not settings.last_dynamic_report_sent:
            # Never sent before, send now
            return True
        
        # Import timezone service here to avoid circular imports
        from .timezone_service import TimezoneService
        from datetime import timedelta
        
        # Convert last sent time to local timezone for comparison
        timezone_service = TimezoneService(SessionLocal())
        user_timezone = settings.timezone or 'UTC'
        last_sent_local = timezone_service.convert_utc_to_local(settings.last_dynamic_report_sent, user_timezone)
        
        # Check based on frequency
        if settings.dynamic_report_frequency == "daily":
            # Send if it's a different day or if it's been more than 20 hours
            # (to handle edge cases around DST changes)
            different_day = now_local.date() != last_sent_local.date()
            time_threshold = (now_utc - settings.last_dynamic_report_sent).total_seconds() >= 72000  # 20 hours
            return different_day and time_threshold
            
        elif settings.dynamic_report_frequency == "weekly":
            # Send if it's been at least 6 days and it's the same day of week or later
            days_since = (now_utc - settings.last_dynamic_report_sent).days
            return days_since >= 6
            
        elif settings.dynamic_report_frequency == "monthly":
            # Send if it's been at least 28 days
            days_since = (now_utc - settings.last_dynamic_report_sent).days
            return days_since >= 28
        
        # Default to weekly behavior for dynamic reports
        days_since = (now_utc - settings.last_dynamic_report_sent).days
        return days_since >= 6
    
    async def _check_and_perform_backups(self):
        """Check if backups should be performed and perform them"""
        db = SessionLocal()
        try:
            backup_settings = db.query(models.BackupSettings).first()
            if not backup_settings:
                logger.debug("No backup settings found")
                return
                
            if not backup_settings.enabled:
                logger.debug("Backups are disabled")
                return
            
            if not all([backup_settings.storage_account, backup_settings.container_name, backup_settings.sas_token]):
                logger.debug("Backup settings incomplete")
                return
            
            # Check if backup is already running
            if backup_settings.last_backup_status == "running":
                logger.debug("Backup is already running")
                return
            
            now = datetime.now(timezone.utc)
            current_hour = now.hour
            
            logger.debug(f"Backup time check: current hour={current_hour}, scheduled={backup_settings.backup_hour}")
            
            # Check if it's time to perform backup
            if current_hour != backup_settings.backup_hour:
                logger.debug(f"Not time for backup (current hour: {current_hour}, scheduled: {backup_settings.backup_hour})")
                return
            
            # Check if we should backup based on frequency and last backup time
            should_backup = self._should_perform_backup(backup_settings, now)
            logger.debug(f"Should perform backup: {should_backup}")
            if not should_backup:
                logger.debug("Backup skipped based on frequency/timing rules")
                return
            
            logger.info(f"Starting scheduled backup at {now.strftime('%H:%M')} UTC")
            
            # Update status to running
            backup_settings.last_backup_status = "running"
            backup_settings.last_backup_error = None
            db.commit()
            
            # Perform backup
            await self._perform_scheduled_backup(backup_settings)
                
        except Exception as e:
            logger.error(f"Error checking and performing backups: {str(e)}")
        finally:
            db.close()
    
    def _should_perform_backup(self, backup_settings, now_utc: datetime) -> bool:
        """
        Determine if a backup should be performed based on frequency and last backup time
        
        Args:
            backup_settings: BackupSettings object
            now_utc: Current UTC datetime
            
        Returns:
            True if backup should be performed, False otherwise
        """
        if not backup_settings.last_backup_time:
            # Never backed up before, backup now
            return True
        
        # Check based on frequency
        if backup_settings.backup_frequency == "daily":
            # Backup if it's been more than 20 hours since last backup
            hours_since = (now_utc - backup_settings.last_backup_time).total_seconds() / 3600
            return hours_since >= 20
            
        elif backup_settings.backup_frequency == "weekly":
            # Backup if it's been at least 6 days
            days_since = (now_utc - backup_settings.last_backup_time).days
            return days_since >= 6
            
        elif backup_settings.backup_frequency == "monthly":
            # Backup if it's been at least 28 days
            days_since = (now_utc - backup_settings.last_backup_time).days
            return days_since >= 28
        
        # Default to daily behavior
        hours_since = (now_utc - backup_settings.last_backup_time).total_seconds() / 3600
        return hours_since >= 20
    
    async def _perform_scheduled_backup(self, backup_settings):
        """Perform the actual backup operation"""
        import os
        
        db = SessionLocal()
        try:
            backup_service = create_backup_service(
                storage_account=backup_settings.storage_account,
                container_name=backup_settings.container_name,
                sas_token=backup_settings.sas_token
            )
            
            # Get database file path
            db_path = "./booking.db"  # Adjust path as needed
            if not os.path.exists(db_path):
                raise FileNotFoundError(f"Database file not found: {db_path}")
            
            # Perform backup
            result = backup_service.upload_database_backup(db_path)
            
            # Update settings with result
            backup_settings.last_backup_time = datetime.now(timezone.utc)
            
            if result["success"]:
                backup_settings.last_backup_status = "success"
                backup_settings.last_backup_error = None
                backup_settings.last_backup_size_mb = result.get("file_size_mb", 0)
                logger.info(f"Scheduled backup completed successfully. Size: {result.get('file_size_mb', 0)} MB")
            else:
                backup_settings.last_backup_status = "failed"
                backup_settings.last_backup_error = result.get("error", "Unknown error")
                logger.error(f"Scheduled backup failed: {result.get('error', 'Unknown error')}")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Scheduled backup operation failed: {str(e)}")
            # Update status to failed
            backup_settings = db.query(models.BackupSettings).first()
            if backup_settings:
                backup_settings.last_backup_status = "failed"
                backup_settings.last_backup_error = str(e)
                backup_settings.last_backup_time = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()


# Global scheduler instance
report_scheduler = ReportScheduler()


async def start_scheduler():
    """Start the global report scheduler"""
    await report_scheduler.start()


async def stop_scheduler():
    """Stop the global report scheduler"""
    await report_scheduler.stop()
