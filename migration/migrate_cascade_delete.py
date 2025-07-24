"""
Migration script to add CASCADE DELETE constraints to parking_lots and parking_spaces relationship.
This will ensure that when a parking lot is deleted, all associated parking spaces and bookings are also deleted.
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
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Copy the database file
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"✅ Database backed up to: {backup_path}")
    return backup_path

def migrate_cascade_delete():
    """Add cascade delete constraints to the database"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return False
    
    # Create backup
    backup_path = backup_database(db_path)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 Starting cascade delete migration...")
        
        # Check if foreign key constraints are enabled
        cursor.execute("PRAGMA foreign_keys;")
        fk_enabled = cursor.fetchone()[0]
        print(f"📋 Foreign key constraints enabled: {bool(fk_enabled)}")
        
        # Temporarily disable foreign key constraints for the migration
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION;")
        
        # Step 1: Create new tables with CASCADE DELETE
        print("📝 Creating new tables with CASCADE DELETE...")
        
        # Create new parking_spaces table with cascade delete
        cursor.execute("""
            CREATE TABLE parking_spaces_new (
                id INTEGER PRIMARY KEY,
                lot_id INTEGER REFERENCES parking_lots(id) ON DELETE CASCADE,
                space_number VARCHAR,
                position_x INTEGER,
                position_y INTEGER,
                width INTEGER,
                height INTEGER,
                color VARCHAR
            );
        """)
        
        # Create new bookings table with cascade delete
        cursor.execute("""
            CREATE TABLE bookings_new (
                id INTEGER PRIMARY KEY,
                space_id INTEGER REFERENCES parking_spaces(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id),
                start_time DATETIME,
                end_time DATETIME,
                license_plate VARCHAR,
                is_cancelled BOOLEAN DEFAULT 0
            );
        """)
        
        # Step 2: Copy data from old tables to new tables
        print("📋 Copying data to new tables...")
        
        # Copy parking spaces data
        cursor.execute("""
            INSERT INTO parking_spaces_new (id, lot_id, space_number, position_x, position_y, width, height, color)
            SELECT id, lot_id, space_number, position_x, position_y, width, height, color
            FROM parking_spaces;
        """)
        
        # Copy bookings data
        cursor.execute("""
            INSERT INTO bookings_new (id, space_id, user_id, start_time, end_time, license_plate, is_cancelled)
            SELECT id, space_id, user_id, start_time, end_time, license_plate, is_cancelled
            FROM bookings;
        """)
        
        # Step 3: Drop old tables and rename new tables
        print("🔄 Replacing old tables with new ones...")
        
        cursor.execute("DROP TABLE bookings;")
        cursor.execute("DROP TABLE parking_spaces;")
        
        cursor.execute("ALTER TABLE parking_spaces_new RENAME TO parking_spaces;")
        cursor.execute("ALTER TABLE bookings_new RENAME TO bookings;")
        
        # Step 4: Recreate indexes
        print("📊 Recreating indexes...")
        
        # Recreate indexes for parking_spaces
        cursor.execute("CREATE INDEX ix_parking_spaces_id ON parking_spaces (id);")
        
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
        
        print(f"✅ Migration completed successfully!")
        print(f"📊 Database contents:")
        print(f"   - Parking lots: {lot_count}")
        print(f"   - Parking spaces: {space_count}")
        print(f"   - Bookings: {booking_count}")
        
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
    print("🚀 Starting CASCADE DELETE migration for parking lots...")
    print("=" * 60)
    
    success = migrate_cascade_delete()
    
    print("=" * 60)
    if success:
        print("✅ Migration completed successfully!")
        print("🔧 Parking lots can now be deleted with proper cascade deletion of spaces and bookings.")
    else:
        print("❌ Migration failed!")
        print("📋 Database has been restored from backup.")
        sys.exit(1)

if __name__ == "__main__":
    main()
