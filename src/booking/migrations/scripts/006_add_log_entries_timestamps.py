"""
Add created_at and updated_at timestamps to log_entries table.

This migration adds the missing timestamp columns to the log_entries table
that were not included in the original timestamp migration.
"""

from sqlalchemy import text
from datetime import datetime, timezone
from ..base import BaseMigration


class AddLogEntriesTimestampsMigration(BaseMigration):
    """Add created_at and updated_at columns to log_entries table."""
    
    version = "006"
    description = "Add created_at and updated_at timestamps to log_entries table"
    
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
        """Add timestamp columns to log_entries table."""
        table = 'log_entries'
        
        # Check if table exists
        if not self._table_exists(table):
            print(f"⚠️  Table '{table}' does not exist, skipping...")
            return
        
        current_time = datetime.now(timezone.utc).isoformat()
        
        try:
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
            raise
        
        self.session.commit()
        print("✅ Log entries timestamp columns migration completed")
    
    def down(self) -> None:
        """Remove timestamp columns from log_entries table."""
        # SQLite doesn't support DROP COLUMN before version 3.35.0
        # For older SQLite versions, we would need to recreate tables
        print("⚠️  SQLite does not support DROP COLUMN in older versions")
        print("   Timestamp column removal not implemented for backward compatibility")
        print("   The columns will remain but won't be used by the application")
    
    def validate(self) -> bool:
        """Validate that log_entries table exists."""
        try:
            return self._table_exists('log_entries')
        except Exception:
            return False
