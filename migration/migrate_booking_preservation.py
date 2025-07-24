"""
Migration script to update booking model for historical data preservation.
This will ensure that when parking lots/spaces are deleted, bookings are preserved 
with space information stored in deleted_space_info field.
"""

import sqlite3
import os
import sys
from datetime import datetime

def get_db_path():
    """Get the database path"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    return os.path.join(project_root, 'booking.db')

def backup_database(db_path):
    """Create a backup of the database"""
    backup_path = f"{db_path}.backup_preservation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Copy the database file
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"✅ Database backed up to: {backup_path}")
    return backup_path

def migrate_booking_preservation():
    """Update booking model for historical data preservation"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return False
    
    # Create backup
    backup_path = backup_database(db_path)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 Starting booking preservation migration...")
        
        # Check if foreign key constraints are enabled
        cursor.execute("PRAGMA foreign_keys;")
        fk_enabled = cursor.fetchone()[0]
        print(f"📋 Foreign key constraints enabled: {bool(fk_enabled)}")
        
        # Temporarily disable foreign key constraints for the migration
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION;")
        
        # Step 1: Create new bookings table with nullable space_id and deleted_space_info
        print("📝 Creating new bookings table with booking preservation...")
        
        cursor.execute("""
            CREATE TABLE bookings_new (
                id INTEGER PRIMARY KEY,
                space_id INTEGER REFERENCES parking_spaces(id) ON DELETE SET NULL,
                user_id INTEGER REFERENCES users(id),
                start_time DATETIME,
                end_time DATETIME,
                license_plate VARCHAR,
                is_cancelled BOOLEAN DEFAULT 0,
                deleted_space_info VARCHAR
            );
        """)
        
        # Step 2: Copy data from old table to new table
        print("📋 Copying data to new bookings table...")
        
        cursor.execute("""
            INSERT INTO bookings_new (id, space_id, user_id, start_time, end_time, license_plate, is_cancelled)
            SELECT id, space_id, user_id, start_time, end_time, license_plate, is_cancelled
            FROM bookings;
        """)
        
        # Step 3: Drop old table and rename new table
        print("🔄 Replacing old bookings table with new one...")
        
        cursor.execute("DROP TABLE bookings;")
        cursor.execute("ALTER TABLE bookings_new RENAME TO bookings;")
        
        # Step 4: Recreate indexes
        print("📊 Recreating indexes...")
        
        # Recreate indexes for bookings
        cursor.execute("CREATE INDEX ix_bookings_id ON bookings (id);")
        
        # Commit transaction
        cursor.execute("COMMIT;")
        
        # Re-enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Verify foreign key constraints
        cursor.execute("PRAGMA foreign_key_check;")
        fk_violations = cursor.fetchall()
        
        if fk_violations:
            print(f"⚠️  Foreign key violations found: {fk_violations}")
            return False
        
        # Get counts to verify migration
        cursor.execute("SELECT COUNT(*) FROM parking_lots;")
        lot_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM parking_spaces;")
        space_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM bookings;")
        booking_count = cursor.fetchone()[0]
        
        # Check how many bookings have deleted_space_info
        cursor.execute("SELECT COUNT(*) FROM bookings WHERE deleted_space_info IS NOT NULL;")
        preserved_booking_count = cursor.fetchone()[0]
        
        print(f"✅ Migration completed successfully!")
        print(f"📊 Database contents:")
        print(f"   - Parking lots: {lot_count}")
        print(f"   - Parking spaces: {space_count}")
        print(f"   - Bookings: {booking_count}")
        print(f"   - Bookings with preserved space info: {preserved_booking_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        
        # Restore from backup
        print("🔄 Restoring from backup...")
        import shutil
        shutil.copy2(backup_path, db_path)
        print("✅ Database restored from backup")
        
        return False

def main():
    """Main migration function"""
    print("🚀 Starting booking preservation migration...")
    print("=" * 60)
    
    success = migrate_booking_preservation()
    
    print("=" * 60)
    if success:
        print("✅ Migration completed successfully!")
        print("🔧 Bookings will now be preserved when parking lots/spaces are deleted.")
        print("📊 Historical booking data will be maintained for reporting purposes.")
    else:
        print("❌ Migration failed!")
        print("📋 Database has been restored from backup.")
        sys.exit(1)

if __name__ == "__main__":
    main()
