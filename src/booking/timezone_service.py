"""
Timezone service for handling timezone conversions across the application
"""
import pytz
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from . import models


class TimezoneService:
    """Service for handling timezone operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self._cached_timezone = None
    
    def get_system_timezone(self) -> str:
        """
        Get the configured system timezone from email settings
        
        Returns:
            Timezone string (defaults to 'UTC' if not configured)
        """
        if self._cached_timezone:
            return self._cached_timezone
            
        settings = self.db.query(models.EmailSettings).first()
        if settings and settings.timezone:
            self._cached_timezone = settings.timezone
            return settings.timezone
        
        self._cached_timezone = 'UTC'
        return 'UTC'
    
    def refresh_timezone_cache(self):
        """Refresh the cached timezone setting"""
        self._cached_timezone = None
    
    def convert_utc_to_local(self, utc_dt: datetime, timezone_name: Optional[str] = None) -> datetime:
        """
        Convert UTC datetime to local timezone
        
        Args:
            utc_dt: UTC datetime to convert
            timezone_name: Target timezone (uses system timezone if not provided)
            
        Returns:
            Datetime in local timezone
        """
        if timezone_name is None:
            timezone_name = self.get_system_timezone()
        
        try:
            # Ensure input is timezone-aware UTC
            if utc_dt.tzinfo is None:
                utc_dt = utc_dt.replace(tzinfo=timezone.utc)
            elif utc_dt.tzinfo != timezone.utc:
                utc_dt = utc_dt.astimezone(timezone.utc)
            
            # Convert to target timezone
            target_tz = pytz.timezone(timezone_name)
            return utc_dt.astimezone(target_tz)
            
        except pytz.exceptions.UnknownTimeZoneError:
            # Fallback to UTC if timezone is invalid
            return utc_dt
    
    def convert_local_to_utc(self, local_dt: datetime, timezone_name: Optional[str] = None) -> datetime:
        """
        Convert local datetime to UTC
        
        Args:
            local_dt: Local datetime to convert
            timezone_name: Source timezone (uses system timezone if not provided)
            
        Returns:
            Datetime in UTC
        """
        if timezone_name is None:
            timezone_name = self.get_system_timezone()
        
        try:
            source_tz = pytz.timezone(timezone_name)
            
            # If datetime is naive, localize it to the source timezone
            if local_dt.tzinfo is None:
                local_dt = source_tz.localize(local_dt)
            
            # Convert to UTC
            return local_dt.astimezone(timezone.utc)
            
        except pytz.exceptions.UnknownTimeZoneError:
            # Fallback: assume input is already UTC
            if local_dt.tzinfo is None:
                return local_dt.replace(tzinfo=timezone.utc)
            return local_dt.astimezone(timezone.utc)
    
    def format_datetime_local(self, utc_dt: datetime, format_str: str = "%d-%m-%Y %H:%M", 
                             timezone_name: Optional[str] = None, include_tz: bool = False) -> str:
        """
        Format UTC datetime in local timezone with consistent format
        
        Args:
            utc_dt: UTC datetime to format
            format_str: Format string for datetime (default: "DD-MM-YYYY HH:MM" in 24h format)
            timezone_name: Target timezone (uses system timezone if not provided)
            include_tz: Whether to include timezone abbreviation (default: False)
            
        Returns:
            Formatted datetime string in "DD-MM-YYYY HH:MM" format
        """
        if timezone_name is None:
            timezone_name = self.get_system_timezone()
        
        try:
            local_dt = self.convert_utc_to_local(utc_dt, timezone_name)
            
            if include_tz:
                # Get timezone abbreviation
                tz_name = local_dt.strftime('%Z')
                if not tz_name:
                    tz_name = timezone_name.split('/')[-1].replace('_', ' ')
                return local_dt.strftime(f"{format_str} {tz_name}")
            else:
                return local_dt.strftime(format_str)
                
        except Exception:
            # Fallback to UTC formatting
            return utc_dt.strftime(format_str)
    
    def format_date_local(self, utc_dt: datetime, timezone_name: Optional[str] = None) -> str:
        """
        Format UTC datetime as date only in local timezone
        
        Args:
            utc_dt: UTC datetime to format
            timezone_name: Target timezone (uses system timezone if not provided)
            
        Returns:
            Formatted date string in "DD-MM-YYYY" format
        """
        return self.format_datetime_local(utc_dt, "%d-%m-%Y", timezone_name, include_tz=False)
    
    def format_time_local(self, utc_dt: datetime, timezone_name: Optional[str] = None) -> str:
        """
        Format UTC datetime as time only in local timezone
        
        Args:
            utc_dt: UTC datetime to format
            timezone_name: Target timezone (uses system timezone if not provided)
            
        Returns:
            Formatted time string in 24h format
        """
        return self.format_datetime_local(utc_dt, "%H:%M", timezone_name, include_tz=False)
    
    def get_local_business_hours(self, timezone_name: Optional[str] = None) -> tuple[int, int]:
        """
        Get business hours in local timezone (6 AM to 11 PM)
        
        Args:
            timezone_name: Target timezone (uses system timezone if not provided)
            
        Returns:
            Tuple of (start_hour, end_hour) in 24-hour format
        """
        # Standard business hours: 6 AM to 11 PM
        return (6, 23)
    
    def is_within_business_hours(self, dt: datetime, timezone_name: Optional[str] = None) -> bool:
        """
        Check if datetime is within business hours in local timezone
        
        Args:
            dt: Datetime to check (assumed to be UTC if timezone-naive)
            timezone_name: Target timezone (uses system timezone if not provided)
            
        Returns:
            True if within business hours, False otherwise
        """
        if timezone_name is None:
            timezone_name = self.get_system_timezone()
        
        try:
            local_dt = self.convert_utc_to_local(dt, timezone_name)
            start_hour, end_hour = self.get_local_business_hours(timezone_name)
            
            return start_hour <= local_dt.hour <= end_hour
            
        except Exception:
            # Fallback to UTC check
            return 6 <= dt.hour <= 23
    
    def get_available_timezones(self) -> list[dict]:
        """
        Get list of available timezones with common ones first
        
        Returns:
            List of timezone dictionaries with 'value', 'label', and 'common' keys
        """
        # Common timezones that are most likely to be used
        common_timezones = [
            'UTC',
            'US/Eastern',
            'US/Central', 
            'US/Mountain',
            'US/Pacific',
            'Europe/London',
            'Europe/Paris',
            'Europe/Berlin',
            'Europe/Rome',
            'Europe/Madrid',
            'Asia/Tokyo',
            'Asia/Shanghai',
            'Asia/Kolkata',
            'Australia/Sydney',
            'Australia/Melbourne',
            'Canada/Eastern',
            'Canada/Central',
            'Canada/Mountain',
            'Canada/Pacific',
        ]
        
        # Get all available timezones
        all_timezones = sorted(pytz.all_timezones)
        
        timezone_list = []
        
        # Add common timezones first
        for tz in common_timezones:
            if tz in all_timezones:
                try:
                    pytz.timezone(tz)  # Validate timezone
                    timezone_list.append({
                        'value': tz,
                        'label': tz.replace('_', ' '),
                        'common': True
                    })
                except pytz.exceptions.UnknownTimeZoneError:
                    pass
        
        # Add remaining timezones
        for tz in all_timezones:
            if tz not in common_timezones:
                try:
                    pytz.timezone(tz)  # Validate timezone
                    timezone_list.append({
                        'value': tz,
                        'label': tz.replace('_', ' '),
                        'common': False
                    })
                except pytz.exceptions.UnknownTimeZoneError:
                    pass
        
        return timezone_list