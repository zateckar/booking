"""
Initial database schema creation.

This migration creates all the base tables for the booking application.
"""

from sqlalchemy import text
from booking.migrations.base import BaseMigration


class InitialSchemaMigration(BaseMigration):
    """Create initial database schema."""
    
    version = "001"
    description = "Create initial database schema"
    
    def up(self) -> None:
        """Create all initial tables."""
        # This migration assumes the database is already initialized
        # with Base.metadata.create_all() during first setup
        
        # We'll just verify that key tables exist
        self.session.execute(text("SELECT COUNT(*) FROM users LIMIT 1"))
        self.session.execute(text("SELECT COUNT(*) FROM parking_lots LIMIT 1"))
        self.session.execute(text("SELECT COUNT(*) FROM parking_spaces LIMIT 1"))
        self.session.execute(text("SELECT COUNT(*) FROM bookings LIMIT 1"))
        
        print("✅ Initial schema verification passed")
    
    def down(self) -> None:
        """Drop all tables (dangerous operation)."""
        # This is intentionally not implemented as it would destroy all data
        raise NotImplementedError("Initial schema rollback is not supported")
    
    def validate(self) -> bool:
        """Validate that required tables exist."""
        try:
            # Check if main tables exist
            required_tables = ['users', 'parking_lots', 'parking_spaces', 'bookings']
            for table in required_tables:
                self.session.execute(text(f"SELECT COUNT(*) FROM {table} LIMIT 1"))
            return True
        except Exception:
            return False
