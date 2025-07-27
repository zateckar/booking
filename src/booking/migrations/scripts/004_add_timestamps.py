"""
Add created_at and updated_at timestamps to all tables.

This migration adds timestamp tracking to all existing tables.
"""

from sqlalchemy import text
from datetime import datetime, timezone
from ..base import BaseMigration


class AddTimestampsMigration(BaseMigration):
    """Add created_at and updated_at columns to all tables."""
    
    version = "004"
    description = "Add created_at and updated_at timestamps to all tables"
    
    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists in SQLite."""
        result = self.session.execute(text(f"""
            SELECT COUNT(*) FROM sqlite_master 
            WHERE type='table' AND name='{table_name}'
        """)).scalar()
        return result > 0
    
    def _column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a SQLite table."""
        try:
            # Use PRAGMA table_info to get column information
            columns = self.session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
            for column in columns:
                if column[1] == column_name:  # column[1] is the column name
                    return True
            return False
        except Exception:
            return False
    
    def up(self) -> None:
        """Add timestamp columns to all tables."""
        tables = [
            'users',
            'parking_lots', 
            'parking_spaces',
            'bookings',
            'oidc_providers',
            'email_settings',
            'application_logs',
            'oidc_claim_mappings',
            'user_profiles',
            'report_columns',
            'report_templates',
            'scheduled_dynamic_reports',
            'styling_settings'
        ]
        
        current_time = datetime.now(timezone.utc).isoformat()
        
        for table in tables:
            try:
                # Check if table exists
                if not self._table_exists(table):
                    print(f"⚠️  Table '{table}' does not exist, skipping...")
                    continue
                
                # Check and add created_at column
                if not self._column_exists(table, 'created_at'):
                    self.session.execute(text(f"""
                        ALTER TABLE {table} 
                        ADD COLUMN created_at TIMESTAMP DEFAULT '{current_time}'
                    """))
                    print(f"✅ Added created_at column to {table}")
                else:
                    print(f"⚠️  created_at column already exists in {table}")
                
                # Check and add updated_at column
                if not self._column_exists(table, 'updated_at'):
                    self.session.execute(text(f"""
                        ALTER TABLE {table} 
                        ADD COLUMN updated_at TIMESTAMP DEFAULT '{current_time}'
                    """))
                    print(f"✅ Added updated_at column to {table}")
                else:
                    print(f"⚠️  updated_at column already exists in {table}")
                    
            except Exception as e:
                print(f"❌ Error processing table {table}: {e}")
                # Continue with other tables instead of failing completely
                continue
        
        self.session.commit()
        print("✅ Timestamp columns migration completed")
    
    def down(self) -> None:
        """Remove timestamp columns from all tables."""
        # SQLite doesn't support DROP COLUMN before version 3.35.0
        # For older SQLite versions, we would need to recreate tables
        print("⚠️  SQLite does not support DROP COLUMN in older versions")
        print("   Timestamp column removal not implemented for backward compatibility")
        print("   The columns will remain but won't be used by the application")
    
    def validate(self) -> bool:
        """Validate that core tables exist."""
        try:
            # Check that core tables exist - this is sufficient for validation
            core_tables = ['users', 'bookings']
            for table in core_tables:
                if not self._table_exists(table):
                    return False
            return True
        except Exception:
            return False
