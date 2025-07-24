#!/usr/bin/env python3
"""
Migration script to add StylingSettings table for branding and styling customization.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from booking.database import engine, SessionLocal
from booking.models.styling import StylingSettings
from booking.models.base import Base
from sqlalchemy import text


def check_table_exists():
    """Check if the styling_settings table already exists"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='styling_settings'
        """))
        return result.fetchone() is not None


def migrate_styling_settings():
    """Create the styling_settings table"""
    print("🎨 Starting StylingSettings migration...")
    
    # Check if table already exists
    if check_table_exists():
        print("✅ styling_settings table already exists. Migration skipped.")
        return
    
    try:
        # Create the table
        StylingSettings.__table__.create(engine)
        print("✅ Created styling_settings table successfully!")
        
        # Create a default settings entry
        db = SessionLocal()
        try:
            default_settings = StylingSettings(
                enabled=False,  # Start with custom styling disabled
                logo_alt_text="Company Logo",
                logo_max_height=50,
                show_logo_in_navbar=True,
                show_logo_on_login=True,
                primary_color="#007bff",
                secondary_color="#6c757d",
                success_color="#28a745",
                danger_color="#dc3545",
                warning_color="#ffc107",
                info_color="#17a2b8",
                light_color="#f8f9fa",
                dark_color="#343a40",
                body_bg_color="#ffffff",
                text_color="#212529",
                link_color="#007bff",
                link_hover_color="#0056b3",
                font_family="system-ui",
                navbar_bg_color="#f8f9fa",
                navbar_text_color="#212529",
                navbar_brand_text="Parking Booking"
            )
            
            db.add(default_settings)
            db.commit()
            print("✅ Created default styling settings!")
            
        except Exception as e:
            print(f"❌ Error creating default settings: {e}")
            db.rollback()
        finally:
            db.close()
            
        print("🎨 StylingSettings migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during styling settings migration: {e}")
        raise


if __name__ == "__main__":
    migrate_styling_settings()
