#!/usr/bin/env python3
"""
Migration script to add display_name column to OIDC providers.

This adds a display_name field to the oidc_providers table to provide
user-friendly names for login buttons, solving issues with special
characters and spaces in issuer names.
"""

import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_display_name():
    """Add display_name column to oidc_providers table."""
    
    try:
        # Connect to the database
        conn = sqlite3.connect('booking.db')
        cursor = conn.cursor()
        
        # Check if display_name column already exists
        cursor.execute("PRAGMA table_info(oidc_providers)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'display_name' in column_names:
            logger.info("display_name column already exists in oidc_providers table")
            return
        
        logger.info("Adding display_name column to oidc_providers table...")
        
        # Add the display_name column
        cursor.execute("ALTER TABLE oidc_providers ADD COLUMN display_name TEXT")
        
        # Update existing providers with a default display name based on issuer
        # Remove protocol and simplify common issuer URLs
        logger.info("Setting default display names for existing providers...")
        cursor.execute("SELECT id, issuer FROM oidc_providers")
        providers = cursor.fetchall()
        
        for provider_id, issuer in providers:
            # Generate a user-friendly display name from the issuer
            display_name = issuer
            
            # Remove https:// or http://
            if display_name.startswith('https://'):
                display_name = display_name[8:]
            elif display_name.startswith('http://'):
                display_name = display_name[7:]
            
            # Remove common OIDC paths
            display_name = display_name.replace('/.well-known/openid_configuration', '')
            display_name = display_name.replace('/oauth2', '')
            display_name = display_name.replace('/auth', '')
            
            # Handle common providers
            if 'google' in display_name.lower():
                display_name = 'Google'
            elif 'microsoft' in display_name.lower() or 'azure' in display_name.lower():
                display_name = 'Microsoft'
            elif 'okta' in display_name.lower():
                display_name = 'Okta'
            elif 'auth0' in display_name.lower():
                display_name = 'Auth0'
            elif 'keycloak' in display_name.lower():
                display_name = 'Keycloak'
            else:
                # For custom domains, use the domain name
                if '/' in display_name:
                    display_name = display_name.split('/')[0]
                
                # Capitalize first letter
                display_name = display_name.capitalize()
            
            logger.info(f"Setting display name for provider {provider_id}: '{issuer}' -> '{display_name}'")
            cursor.execute(
                "UPDATE oidc_providers SET display_name = ? WHERE id = ?",
                (display_name, provider_id)
            )
        
        # Commit the changes
        conn.commit()
        logger.info("Successfully added display_name column and updated existing providers")
        
    except sqlite3.Error as e:
        logger.error(f"Database error during migration: {e}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def verify_migration():
    """Verify that the migration was successful."""
    try:
        conn = sqlite3.connect('booking.db')
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute("PRAGMA table_info(oidc_providers)")
        columns = cursor.fetchall()
        
        logger.info("Current oidc_providers table structure:")
        for column in columns:
            logger.info(f"  {column[1]} ({column[2]})")
        
        # Check current providers
        cursor.execute("SELECT id, issuer, display_name FROM oidc_providers")
        providers = cursor.fetchall()
        
        if providers:
            logger.info("Current OIDC providers:")
            for provider_id, issuer, display_name in providers:
                logger.info(f"  ID {provider_id}: '{issuer}' -> '{display_name}'")
        else:
            logger.info("No OIDC providers found in database")
            
    except Exception as e:
        logger.error(f"Error during verification: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("Starting OIDC display_name migration...")
    migrate_display_name()
    verify_migration()
    logger.info("Migration completed successfully!")
