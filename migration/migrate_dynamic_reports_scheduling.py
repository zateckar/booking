"""
Migration script to add dynamic reports scheduling fields to EmailSettings table
"""

import sqlite3
import sys
from datetime import datetime

def migrate_dynamic_reports_scheduling():
    """Add dynamic reports scheduling fields to email_settings table"""
    
    try:
        # Connect to the database
        conn = sqlite3.connect('booking.db')
        cursor = conn.cursor()
        
        print("Starting dynamic reports scheduling migration...")
        
        # Check if email_settings table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='email_settings'
        """)
        
        if not cursor.fetchone():
            print("email_settings table does not exist. Creating it...")
            # Create the table with all fields including new ones
            cursor.execute("""
                CREATE TABLE email_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sendgrid_api_key TEXT,
                    from_email TEXT,
                    from_name TEXT,
                    booking_confirmation_enabled BOOLEAN DEFAULT 0,
                    reports_enabled BOOLEAN DEFAULT 0,
                    report_recipients TEXT,
                    report_schedule_hour INTEGER DEFAULT 9,
                    report_frequency TEXT DEFAULT 'weekly',
                    last_report_sent TIMESTAMP,
                    timezone TEXT DEFAULT 'UTC',
                    dynamic_reports_enabled BOOLEAN DEFAULT 0,
                    dynamic_report_recipients TEXT,
                    dynamic_report_schedule_hour INTEGER DEFAULT 9,
                    dynamic_report_frequency TEXT DEFAULT 'weekly',
                    dynamic_report_template_id INTEGER,
                    last_dynamic_report_sent TIMESTAMP
                )
            """)
            print("Created email_settings table with dynamic reports fields")
        else:
            # Check which columns already exist
            cursor.execute("PRAGMA table_info(email_settings)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            print(f"Existing columns: {existing_columns}")
            
            # Add missing columns
            new_columns = [
                ('dynamic_reports_enabled', 'BOOLEAN DEFAULT 0'),
                ('dynamic_report_recipients', 'TEXT'),
                ('dynamic_report_schedule_hour', 'INTEGER DEFAULT 9'),
                ('dynamic_report_frequency', 'TEXT DEFAULT \'weekly\''),
                ('dynamic_report_template_id', 'INTEGER'),
                ('last_dynamic_report_sent', 'TIMESTAMP')
            ]
            
            for column_name, column_def in new_columns:
                if column_name not in existing_columns:
                    print(f"Adding column: {column_name}")
                    cursor.execute(f"ALTER TABLE email_settings ADD COLUMN {column_name} {column_def}")
                else:
                    print(f"Column {column_name} already exists, skipping")
        
        # Commit the changes
        conn.commit()
        print("Migration completed successfully!")
        
        # Verify the table structure
        cursor.execute("PRAGMA table_info(email_settings)")
        columns = cursor.fetchall()
        print("\nFinal table structure:")
        for column in columns:
            print(f"  {column[1]} ({column[2]})")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    return True

def verify_migration():
    """Verify that the migration was successful"""
    try:
        conn = sqlite3.connect('booking.db')
        cursor = conn.cursor()
        
        # Check that all required columns exist
        cursor.execute("PRAGMA table_info(email_settings)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        required_columns = [
            'dynamic_reports_enabled',
            'dynamic_report_recipients', 
            'dynamic_report_schedule_hour',
            'dynamic_report_frequency',
            'dynamic_report_template_id',
            'last_dynamic_report_sent'
        ]
        
        missing_columns = []
        for col in required_columns:
            if col not in columns:
                missing_columns.append(col)
        
        if missing_columns:
            print(f"Verification failed. Missing columns: {missing_columns}")
            return False
        
        print("Verification successful. All dynamic reports columns are present.")
        return True
        
    except Exception as e:
        print(f"Verification error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Dynamic Reports Scheduling Migration")
    print("=" * 50)
    
    # Run migration
    success = migrate_dynamic_reports_scheduling()
    
    if success:
        # Verify migration
        if verify_migration():
            print("\n✅ Migration completed and verified successfully!")
        else:
            print("\n❌ Migration completed but verification failed!")
            sys.exit(1)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
