"""
Migration script to add OIDC claims mapping functionality
This adds dynamic claims mapping and enhanced reporting capabilities
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

# Add the src directory to the path to import models
sys.path.insert(0, str(Path(__file__).parent / "src"))

from booking.database import SQLALCHEMY_DATABASE_URL, engine
from booking.models import Base, OIDCClaimMapping, UserProfile, ReportColumn, ReportTemplate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to add OIDC claims mapping tables"""
    
    try:
        logger.info(f"Connecting to database: {SQLALCHEMY_DATABASE_URL}")
        
        # Create tables
        logger.info("Creating new tables for OIDC claims mapping...")
        
        # Create the new tables
        OIDCClaimMapping.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created oidc_claim_mappings table")
        
        UserProfile.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created user_profiles table")
        
        ReportColumn.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created report_columns table")
        
        ReportTemplate.__table__.create(engine, checkfirst=True)
        logger.info("✓ Created report_templates table")
        
        # Create session for data insertion
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # Insert default report columns for static fields
            default_columns = [
                {"column_name": "email", "display_label": "Email", "column_type": "static", "data_type": "string", "sort_order": 1},
                {"column_name": "is_admin", "display_label": "Is Admin", "column_type": "static", "data_type": "boolean", "sort_order": 2},
                {"column_name": "total_bookings", "display_label": "Total Bookings", "column_type": "calculated", "data_type": "number", "sort_order": 10},
                {"column_name": "total_hours", "display_label": "Total Hours", "column_type": "calculated", "data_type": "number", "sort_order": 11},
                {"column_name": "avg_duration", "display_label": "Avg Duration (hours)", "column_type": "calculated", "data_type": "number", "sort_order": 12},
                {"column_name": "parking_lots_used", "display_label": "Parking Lots Used", "column_type": "calculated", "data_type": "number", "sort_order": 13},
                {"column_name": "license_plates", "display_label": "License Plates Used", "column_type": "calculated", "data_type": "number", "sort_order": 14},
            ]
            
            for col_data in default_columns:
                # Check if column already exists
                existing = db.query(ReportColumn).filter(ReportColumn.column_name == col_data["column_name"]).first()
                if not existing:
                    column = ReportColumn(**col_data)
                    db.add(column)
            
            db.commit()
            logger.info("✓ Inserted default report columns")
            
            # Insert default email claim mapping (required for authentication)
            existing_email_mapping = db.query(OIDCClaimMapping).filter(
                OIDCClaimMapping.claim_name == "email"
            ).first()
            
            if not existing_email_mapping:
                email_mapping = OIDCClaimMapping(
                    claim_name="email",
                    mapped_field_name="email",
                    mapping_type="string",
                    is_required=True,
                    display_label="Email",
                    description="User email address - required for authentication"
                )
                db.add(email_mapping)
                db.commit()
                logger.info("✓ Created default email claim mapping")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error inserting default data: {e}")
            raise
        finally:
            db.close()
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
