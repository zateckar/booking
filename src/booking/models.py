"""
Backward compatibility module for models.

This module imports all models from the new modular structure
to maintain compatibility with existing imports.

DEPRECATED: Import models directly from src.booking.models package instead.
Example: from src.booking.models import User, Booking
"""

# Import all models from the new modular structure
from .models import *

# Explicitly import for backward compatibility
from .models import (
    Base,
    BaseModel,
    TimezoneAwareDateTime,
    User,
    UserProfile,
    ParkingLot,
    ParkingSpace,
    Booking,
    OIDCProvider,
    OIDCClaimMapping,
    AppConfig,
    BackupSettings,
    EmailSettings,
    LogEntry,
    DynamicReportTemplate,
    ReportColumn,
    ReportTemplate,
)

# Keep the original __all__ for compatibility
__all__ = [
    "Base",
    "BaseModel",
    "TimezoneAwareDateTime", 
    "User",
    "UserProfile",
    "ParkingLot",
    "ParkingSpace",
    "Booking",
    "OIDCProvider",
    "OIDCClaimMapping",
    "AppConfig",
    "BackupSettings",
    "EmailSettings",
    "LogEntry",
    "DynamicReportTemplate",
    "ReportColumn",
    "ReportTemplate",
]
