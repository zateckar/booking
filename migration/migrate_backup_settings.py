#!/usr/bin/env python3
"""
Database migration script to add BackupSettings table
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine, inspect
from src.booking.database import SQLALCHEMY_DATABASE_URL, Base
from src.booking.models import BackupSettings

def migrate_backup_settings():
    """Add BackupSettings table to the database"""
    
    # Create engine
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    
    # Check if table already exists
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if 'backup_settings' in existing_tables:
        print("✅ BackupSettings table already exists. No migration needed.")
        return
    
    try:
        # Create the table
        print("🔄 Creating BackupSettings table...")
        BackupSettings.__table__.create(engine)
        print("✅ BackupSettings table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating BackupSettings table: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Starting BackupSettings table migration...")
    migrate_backup_settings()
    print("Migration completed!")
