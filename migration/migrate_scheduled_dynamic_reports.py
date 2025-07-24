#!/usr/bin/env python3
"""
Migration script to create the scheduled_dynamic_reports table
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine, inspect
from src.booking.database import SQLALCHEMY_DATABASE_URL, Base
from src.booking.models import ScheduledDynamicReport

def migrate_scheduled_dynamic_reports():
    """Create the scheduled_dynamic_reports table"""
    
    # Create engine
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    
    # Check if table already exists
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if 'scheduled_dynamic_reports' in existing_tables:
        print("✅ ScheduledDynamicReport table already exists. No migration needed.")
        return
    
    try:
        # Create the table
        print("🔄 Creating ScheduledDynamicReport table...")
        ScheduledDynamicReport.__table__.create(engine)
        print("✅ ScheduledDynamicReport table created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating ScheduledDynamicReport table: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Starting ScheduledDynamicReport table migration...")
    migrate_scheduled_dynamic_reports()
    print("Migration completed!")
