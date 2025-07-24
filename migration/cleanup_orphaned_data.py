"""
Cleanup script to remove orphaned parking spaces and bookings after migration.
This will fix the validation errors caused by spaces with None lot_id values.
"""

import sqlite3
import os
from datetime import datetime

def get_db_path():
    """Get the database path"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    return os.path.join(project_root, 'booking.db')

def cleanup_orphaned_data():
    """Clean up orphaned parking spaces and bookings"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🧹 Starting cleanup of orphaned data...")
        
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        # Begin transaction
        cursor.execute("BEGIN TRANSACTION;")
        
        # Step 1: Find orphaned spaces
        cursor.execute('''
            SELECT ps.id, ps.lot_id 
            FROM parking_spaces ps 
            LEFT JOIN parking_lots pl ON ps.lot_id = pl.id 
            WHERE pl.id IS NULL OR ps.lot_id IS NULL;
        ''')
        orphaned_spaces = cursor.fetchall()
        
        if orphaned_spaces:
            print(f"📋 Found {len(orphaned_spaces)} orphaned parking spaces")
            space_ids = [str(space[0]) for space in orphaned_spaces]
            
            # Step 2: Find bookings referencing orphaned spaces
            if space_ids:
                cursor.execute(f'''
                    SELECT COUNT(*) FROM bookings 
                    WHERE space_id IN ({','.join(space_ids)});
                ''')
                orphaned_booking_count = cursor.fetchone()[0]
                
                if orphaned_booking_count > 0:
                    print(f"📋 Found {orphaned_booking_count} bookings referencing orphaned spaces")
                    
                    # Delete bookings referencing orphaned spaces
                    cursor.execute(f'''
                        DELETE FROM bookings 
                        WHERE space_id IN ({','.join(space_ids)});
                    ''')
                    print(f"🗑️  Deleted {orphaned_booking_count} orphaned bookings")
                
                # Step 3: Delete orphaned spaces
                cursor.execute(f'''
                    DELETE FROM parking_spaces 
                    WHERE id IN ({','.join(space_ids)});
                ''')
                print(f"🗑️  Deleted {len(orphaned_spaces)} orphaned parking spaces")
        else:
            print("✅ No orphaned parking spaces found")
        
        # Step 4: Verify data integrity after cleanup
        cursor.execute("PRAGMA foreign_key_check;")
        violations = cursor.fetchall()
        
        if violations:
            print(f"⚠️  Foreign key violations still exist: {violations}")
            cursor.execute("ROLLBACK;")
            return False
        
        # Commit transaction
        cursor.execute("COMMIT;")
        
        # Get final counts
        cursor.execute("SELECT COUNT(*) FROM parking_lots;")
        lot_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM parking_spaces;")
        space_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM bookings;")
        booking_count = cursor.fetchone()[0]
        
        print(f"✅ Cleanup completed successfully!")
        print(f"📊 Final database contents:")
        print(f"   - Parking lots: {lot_count}")
        print(f"   - Parking spaces: {space_count}")
        print(f"   - Bookings: {booking_count}")
        
        # Final verification - check for any remaining orphaned data
        cursor.execute('''
            SELECT COUNT(*) FROM parking_spaces ps 
            LEFT JOIN parking_lots pl ON ps.lot_id = pl.id 
            WHERE pl.id IS NULL OR ps.lot_id IS NULL;
        ''')
        remaining_orphaned = cursor.fetchone()[0]
        
        if remaining_orphaned > 0:
            print(f"⚠️  Warning: {remaining_orphaned} orphaned spaces still remain")
            return False
        else:
            print("✅ No orphaned data remaining")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False

def main():
    """Main cleanup function"""
    print("🚀 Starting orphaned data cleanup...")
    print("=" * 60)
    
    success = cleanup_orphaned_data()
    
    print("=" * 60)
    if success:
        print("✅ Cleanup completed successfully!")
        print("🔧 Database integrity restored.")
    else:
        print("❌ Cleanup failed!")

if __name__ == "__main__":
    main()
