#!/usr/bin/env python3
"""
Migration script to add new columns to log_entries table
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import create_engine, text, Column, String, Integer, JSON
from src.booking.database import SQLALCHEMY_DATABASE_URL

def migrate_logs_schema():
    """Add new columns to log_entries table"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()
        
        try:
            print("Adding new columns to log_entries table...")
            
            # Add new columns to log_entries table
            columns_to_add = [
                "ALTER TABLE log_entries ADD COLUMN module TEXT",
                "ALTER TABLE log_entries ADD COLUMN function TEXT", 
                "ALTER TABLE log_entries ADD COLUMN line_number INTEGER",
                "ALTER TABLE log_entries ADD COLUMN request_id TEXT",
                "ALTER TABLE log_entries ADD COLUMN extra_data JSON"
            ]
            
            for sql in columns_to_add:
                try:
                    conn.execute(text(sql))
                    print(f"✅ Added column: {sql.split('ADD COLUMN ')[1]}")
                except Exception as e:
                    if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                        print(f"⚠️  Column already exists: {sql.split('ADD COLUMN ')[1]}")
                    else:
                        print(f"❌ Error adding column: {e}")
                        raise
            
            # Create indexes for new columns
            indexes_to_create = [
                "CREATE INDEX IF NOT EXISTS idx_log_entries_request_id ON log_entries(request_id)",
            ]
            
            for sql in indexes_to_create:
                try:
                    conn.execute(text(sql))
                    print(f"✅ Created index: {sql}")
                except Exception as e:
                    print(f"⚠️  Index creation: {e}")
            
            # Commit the transaction
            trans.commit()
            print("✅ Log entries schema migration completed successfully!")
            
        except Exception as e:
            # Rollback on error
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate_logs_schema()
