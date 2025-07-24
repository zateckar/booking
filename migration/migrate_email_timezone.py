#!/usr/bin/env python3
"""
Migration script to add timezone column to EmailSettings table.

This fixes the error: 'EmailSettings' object has no attribute 'timezone'
"""

import sys
import os
import sqlite3
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def migrate_email_timezone():
    """Add timezone column to email_settings table"""
    
    db_path = "booking.db"
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found. No migration needed.")
        return True
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if timezone column already exists
        cursor.execute("PRAGMA table_info(email_settings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'timezone' in columns:
            print("timezone column already exists in email_settings table. No migration needed.")
            conn.close()
            return True
        
        print("Adding timezone column to email_settings table...")
        
        # Add timezone column with default value UTC
        cursor.execute("""
            ALTER TABLE email_settings 
            ADD COLUMN timezone TEXT DEFAULT 'UTC'
        """)
        
        # Update any existing rows to have the default timezone
        cursor.execute("""
            UPDATE email_settings 
            SET timezone = 'UTC' 
            WHERE timezone IS NULL
        """)
        
        # Commit changes
        conn.commit()
        
        print("✓ Successfully added timezone column to email_settings table")
        
        # Verify the migration
        cursor.execute("PRAGMA table_info(email_settings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'timezone' in columns:
            print("✓ Migration verified: timezone column exists")
        else:
            print("✗ Migration verification failed: timezone column not found")
            conn.close()
            return False
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"✗ Database error during migration: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during migration: {e}")
        return False

def main():
    """Main migration function"""
    print("=" * 60)
    print("Email Timezone Migration")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = migrate_email_timezone()
    
    print()
    if success:
        print("✓ Migration completed successfully!")
        print()
        print("The EmailSettings timezone attribute error should now be fixed.")
        print("You can restart the application.")
    else:
        print("✗ Migration failed!")
        print()
        print("Please check the error messages above and try again.")
        print("You may need to fix any database issues manually.")
    
    print("=" * 60)
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
