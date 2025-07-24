"""
Schema version management for the booking application.

This module defines the schema version requirements and provides
utilities for validating database compatibility.
"""

from typing import Optional, Tuple
import os
from dataclasses import dataclass


@dataclass
class SchemaRequirement:
    """
    Defines schema version requirements for the application.
    """
    required_version: str  # Exact version required
    minimum_version: Optional[str] = None  # Minimum compatible version
    maximum_version: Optional[str] = None  # Maximum compatible version
    description: str = ""


class SchemaVersionManager:
    """
    Manages schema version requirements and compatibility checks.
    """
    
    # Define the schema requirements for this application version
    CURRENT_SCHEMA_REQUIREMENT = SchemaRequirement(
        required_version="002",
        minimum_version="001", 
        maximum_version="002",
        description="Booking application v1.0 - requires user cascade delete support"
    )
    
    @classmethod
    def get_required_version(cls) -> str:
        """Get the schema version required by this application."""
        # Allow override via environment variable for testing/deployment flexibility
        env_version = os.getenv("REQUIRED_SCHEMA_VERSION")
        if env_version:
            return env_version
        return cls.CURRENT_SCHEMA_REQUIREMENT.required_version
    
    @classmethod
    def get_minimum_version(cls) -> Optional[str]:
        """Get the minimum schema version compatible with this application."""
        env_min = os.getenv("MINIMUM_SCHEMA_VERSION")
        if env_min:
            return env_min
        return cls.CURRENT_SCHEMA_REQUIREMENT.minimum_version
    
    @classmethod
    def get_maximum_version(cls) -> Optional[str]:
        """Get the maximum schema version compatible with this application."""
        env_max = os.getenv("MAXIMUM_SCHEMA_VERSION")
        if env_max:
            return env_max
        return cls.CURRENT_SCHEMA_REQUIREMENT.maximum_version
    
    @classmethod
    def is_version_compatible(cls, database_version: str) -> Tuple[bool, str]:
        """
        Check if a database schema version is compatible with this application.
        
        Returns:
            Tuple of (is_compatible, reason)
        """
        required = cls.get_required_version()
        minimum = cls.get_minimum_version()
        maximum = cls.get_maximum_version()
        
        # Exact match is always compatible
        if database_version == required:
            return True, f"Database schema version {database_version} matches required version {required}"
        
        # Check minimum version requirement
        if minimum and cls._compare_versions(database_version, minimum) < 0:
            return False, f"Database schema version {database_version} is below minimum required version {minimum}"
        
        # Check maximum version requirement
        if maximum and cls._compare_versions(database_version, maximum) > 0:
            return False, f"Database schema version {database_version} is above maximum supported version {maximum}"
        
        # If we have min/max range, check if we're within it
        if minimum and maximum:
            if cls._compare_versions(database_version, minimum) >= 0 and cls._compare_versions(database_version, maximum) <= 0:
                return True, f"Database schema version {database_version} is within compatible range {minimum}-{maximum}"
        
        # Fallback: not compatible
        return False, f"Database schema version {database_version} is not compatible with application requirements"
    
    @classmethod
    def _compare_versions(cls, version1: str, version2: str) -> int:
        """
        Compare two version strings.
        
        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        # Simple numeric comparison for our 3-digit versions (001, 002, etc.)
        try:
            v1_num = int(version1)
            v2_num = int(version2)
            return (v1_num > v2_num) - (v1_num < v2_num)
        except ValueError:
            # Fallback to string comparison
            return (version1 > version2) - (version1 < version2)
    
    @classmethod
    def get_schema_info(cls) -> dict:
        """Get complete schema requirement information."""
        return {
            "required_version": cls.get_required_version(),
            "minimum_version": cls.get_minimum_version(),
            "maximum_version": cls.get_maximum_version(),
            "description": cls.CURRENT_SCHEMA_REQUIREMENT.description
        }


def validate_database_compatibility(applied_migrations: dict) -> Tuple[bool, str, dict]:
    """
    Validate that the current database schema is compatible with this application.
    
    Args:
        applied_migrations: Dictionary of applied migrations from MigrationManager
    
    Returns:
        Tuple of (is_compatible, message, details)
    """
    schema_manager = SchemaVersionManager()
    
    if not applied_migrations:
        return False, "No migrations have been applied to the database", {
            "current_version": None,
            "required_version": schema_manager.get_required_version(),
            "issue": "database_not_initialized"
        }
    
    # Get the highest applied migration version as current schema version
    current_version = max(applied_migrations.keys(), key=lambda x: int(x))
    
    # Check if any migrations failed
    failed_migrations = [v for v in applied_migrations.values() if v.status == "failed"]
    if failed_migrations:
        return False, f"Database has failed migrations: {[m.version for m in failed_migrations]}", {
            "current_version": current_version,
            "required_version": schema_manager.get_required_version(),
            "issue": "failed_migrations",
            "failed_migrations": [m.version for m in failed_migrations]
        }
    
    # Check version compatibility
    is_compatible, reason = schema_manager.is_version_compatible(current_version)
    
    details = {
        "current_version": current_version,
        "required_version": schema_manager.get_required_version(),
        "minimum_version": schema_manager.get_minimum_version(),
        "maximum_version": schema_manager.get_maximum_version(),
        "is_compatible": is_compatible,
        "reason": reason
    }
    
    return is_compatible, reason, details
