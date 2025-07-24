"""
Migration script to add scopes column to OIDC providers table
"""
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_oidc_scopes():
    """Add scopes column to oidc_providers table if it doesn't exist"""
    try:
        # Connect to the database
        conn = sqlite3.connect('booking.db')
        cursor = conn.cursor()
        
        # Check if the scopes column already exists
        cursor.execute("PRAGMA table_info(oidc_providers)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'scopes' not in columns:
            logger.info("Adding 'scopes' column to oidc_providers table...")
            
            # Add the scopes column with default value
            cursor.execute("""
                ALTER TABLE oidc_providers 
                ADD COLUMN scopes TEXT DEFAULT 'openid email profile'
            """)
            
            # Update existing providers to have the default scopes
            cursor.execute("""
                UPDATE oidc_providers 
                SET scopes = 'openid email profile' 
                WHERE scopes IS NULL OR scopes = ''
            """)
            
            conn.commit()
            logger.info("Successfully added 'scopes' column to oidc_providers table")
            
            # Verify the migration
            cursor.execute("SELECT issuer, scopes FROM oidc_providers")
            providers = cursor.fetchall()
            logger.info(f"Updated {len(providers)} OIDC providers with default scopes:")
            for provider in providers:
                logger.info(f"  - {provider[0]}: '{provider[1]}'")
                
        else:
            logger.info("'scopes' column already exists in oidc_providers table")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_oidc_scopes()
