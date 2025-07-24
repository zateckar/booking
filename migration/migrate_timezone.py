#!/usr/bin/env python3
"""
Migration script to add timezone column to email_settings table
"""
import sqlite3
import sys
from pathlib import Path

def migrate_database():
    """Add timezone column to email_settings table"""
    db_path = Path("booking.db")
    
    if not db_path.exists():
        print("Database file 'booking.db' not found!")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if timezone column already exists
        cursor.execute("PRAGMA table_info(email_settings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'timezone' in columns:
            print("Timezone column already exists in email_settings table")
            conn.close()
            return True
        
        # Add the timezone column with default value 'UTC'
        cursor.execute("ALTER TABLE email_settings ADD COLUMN timezone TEXT DEFAULT 'UTC'")
        
        # Update existing records to have UTC timezone
        cursor.execute("UPDATE email_settings SET timezone = 'UTC' WHERE timezone IS NULL")
        
        # Commit the changes
        conn.commit()
        conn.close()
        
        print("Successfully added timezone column to email_settings table")
        return True
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)