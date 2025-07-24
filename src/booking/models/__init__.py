"""
SQLAlchemy models for the booking application.

This package contains all database models organized by domain:
- base: Base model classes and utilities
- user: User and user profile models
- parking: Parking lot and space models
- booking: Booking-related models
- oidc: OIDC provider and claims mapping models
- config: Application configuration models
- logs: Logging models
- reports: Report template models
"""

# Import all models to maintain backward compatibility
from ..database import Base  # Import Base from database for backward compatibility
from .base import BaseModel, TimezoneAwareDateTime
from .user import User, UserProfile
from .parking import ParkingLot, ParkingSpace
from .booking import Booking
from .oidc import OIDCProvider, OIDCClaimMapping
from .config import AppConfig, BackupSettings, EmailSettings
from .logs import LogEntry
from .reports import DynamicReportTemplate, ReportColumn, ReportTemplate
from .scheduled_reports import ScheduledDynamicReport
from .styling import StylingSettings

# Add alias for backward compatibility
ApplicationLog = LogEntry

# Export all models for easy import
__all__ = [
    # Database base
    "Base",
    
    # Base classes
    "BaseModel",
    "TimezoneAwareDateTime",
    
    # User models
    "User",
    "UserProfile",
    
    # Parking models
    "ParkingLot",
    "ParkingSpace",
    
    # Booking models
    "Booking",
    
    # OIDC models
    "OIDCProvider",
    "OIDCClaimMapping",
    
    # Configuration models
    "AppConfig",
    "BackupSettings", 
    "EmailSettings",
    "StylingSettings",
    
    # Logging models
    "LogEntry",
    "ApplicationLog",  # Alias for LogEntry
    
    # Report models
    "DynamicReportTemplate",
    "ReportColumn",
    "ReportTemplate",
    "ScheduledDynamicReport",
]
