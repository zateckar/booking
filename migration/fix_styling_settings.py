#!/usr/bin/env python3
"""
Fix script to update existing styling settings with proper default values.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from booking.database import SessionLocal
from booking.models.styling import StylingSettings


def fix_styling_settings():
    """Update existing styling settings with proper default values"""
    print("🔧 Fixing styling settings...")
    
    db = SessionLocal()
    try:
        # Get existing settings
        settings = db.query(StylingSettings).first()
        
        if not settings:
            print("❌ No styling settings found. Please run migrate_styling_settings.py first.")
            return
        
        # Update any None values with defaults
        updated = False
        
        if settings.light_color is None:
            settings.light_color = "#f8f9fa"
            updated = True
            print("✅ Fixed light_color")
            
        if settings.dark_color is None:
            settings.dark_color = "#343a40"
            updated = True
            print("✅ Fixed dark_color")
            
        if settings.navbar_brand_text is None:
            settings.navbar_brand_text = "Parking Booking"
            updated = True
            print("✅ Fixed navbar_brand_text")
            
        if settings.logo_alt_text is None:
            settings.logo_alt_text = "Company Logo"
            updated = True
            print("✅ Fixed logo_alt_text")
            
        if settings.font_family is None:
            settings.font_family = "system-ui"
            updated = True
            print("✅ Fixed font_family")
            
        # Ensure all color fields have defaults
        color_defaults = {
            'primary_color': '#007bff',
            'secondary_color': '#6c757d',
            'success_color': '#28a745',
            'danger_color': '#dc3545',
            'warning_color': '#ffc107',
            'info_color': '#17a2b8',
            'body_bg_color': '#ffffff',
            'text_color': '#212529',
            'link_color': '#007bff',
            'link_hover_color': '#0056b3',
            'navbar_bg_color': '#f8f9fa',
            'navbar_text_color': '#212529'
        }
        
        for field, default_value in color_defaults.items():
            current_value = getattr(settings, field)
            if current_value is None:
                setattr(settings, field, default_value)
                updated = True
                print(f"✅ Fixed {field}")
        
        # Ensure numeric fields have defaults
        if settings.logo_max_height is None:
            settings.logo_max_height = 50
            updated = True
            print("✅ Fixed logo_max_height")
            
        # Ensure boolean fields have defaults
        if settings.enabled is None:
            settings.enabled = False
            updated = True
            print("✅ Fixed enabled")
            
        if settings.show_logo_in_navbar is None:
            settings.show_logo_in_navbar = True
            updated = True
            print("✅ Fixed show_logo_in_navbar")
            
        if settings.show_logo_on_login is None:
            settings.show_logo_on_login = True
            updated = True
            print("✅ Fixed show_logo_on_login")
        
        if updated:
            db.commit()
            print("🔧 Styling settings fixed successfully!")
        else:
            print("✅ No fixes needed - styling settings are already correct.")
            
    except Exception as e:
        print(f"❌ Error fixing styling settings: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_styling_settings()
