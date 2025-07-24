#!/usr/bin/env python3
"""
Migration script to add login_logo_max_height column to the styling_settings table.
This allows separate logo sizing for navbar and login page.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from booking.database import engine, SessionLocal
from sqlalchemy import text


def check_column_exists():
    """Check if the login_logo_max_height column already exists"""
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(styling_settings)"))
        columns = [row[1] for row in result.fetchall()]
        return 'login_logo_max_height' in columns


def check_table_exists():
    """Check if the styling_settings table exists"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='styling_settings'
        """))
        return result.fetchone() is not None


def migrate_login_logo_size():
    """Add login_logo_max_height column to styling_settings table"""
    print("🎨 Starting login logo size migration...")
    
    # Check if table exists
    if not check_table_exists():
        print("❌ styling_settings table does not exist. Please run migrate_styling_settings.py first.")
        return
    
    # Check if column already exists
    if check_column_exists():
        print("✅ login_logo_max_height column already exists. Migration skipped.")
        return
    
    try:
        # Add the new column
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE styling_settings 
                ADD COLUMN login_logo_max_height INTEGER DEFAULT 100
            """))
            conn.commit()
        
        print("✅ Added login_logo_max_height column successfully!")
        
        # Update existing records to have the default value
        db = SessionLocal()
        try:
            db.execute(text("""
                UPDATE styling_settings 
                SET login_logo_max_height = 100 
                WHERE login_logo_max_height IS NULL
            """))
            db.commit()
            print("✅ Updated existing records with default login logo size!")
            
        except Exception as e:
            print(f"❌ Error updating existing records: {e}")
            db.rollback()
        finally:
            db.close()
            
        print("🎨 Login logo size migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during login logo size migration: {e}")
        raise


if __name__ == "__main__":
    migrate_login_logo_size()
