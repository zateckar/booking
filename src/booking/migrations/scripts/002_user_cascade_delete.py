"""
User cascade delete migration.

This migration modifies the bookings table to allow user deletion
by making user_id nullable and setting up proper foreign key constraints.
"""

from sqlalchemy import text
from booking.migrations.base import BaseMigration


class UserCascadeDeleteMigration(BaseMigration):
    """Fix user deletion by allowing bookings to have NULL user_id when user is deleted."""
    
    version = "002"
    description = "Allow user deletion with NULL user_id in bookings"
    
    def up(self) -> None:
        """Migrate to allow user deletion by making user_id nullable in bookings."""
        
        # Check if this migration was already applied manually
        try:
            # Test if we can insert a booking with NULL user_id
            self.session.execute(text("""
                INSERT INTO bookings (space_id, user_id, start_time, end_time, license_plate, is_cancelled)
                VALUES (NULL, NULL, datetime('now'), datetime('now', '+1 hour'), 'TEST-MIGRATION', 0)
            """))
            test_id = self.session.execute(text("SELECT last_insert_rowid()")).fetchone()[0]
            self.session.execute(text(f"DELETE FROM bookings WHERE id = {test_id}"))
            self.session.commit()
            
            print("✅ User cascade delete already supported - migration skipped")
            return
        except Exception:
            # Migration is needed
            pass
        
        print("🔄 Applying user cascade delete migration...")
        
        # Step 1: Clean up any previous failed migration attempts
        try:
            self.session.execute(text("DROP TABLE IF EXISTS bookings_new"))
            print("🧹 Cleaned up any existing bookings_new table")
        except:
            pass
        
        # Step 2: Create a new bookings table with nullable user_id and proper foreign key
        self.session.execute(text("""
            CREATE TABLE bookings_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                space_id INTEGER,
                user_id INTEGER,
                start_time DATETIME,
                end_time DATETIME,
                license_plate VARCHAR,
                is_cancelled BOOLEAN DEFAULT 0,
                deleted_space_info VARCHAR,
                FOREIGN KEY(space_id) REFERENCES parking_spaces (id) ON DELETE SET NULL,
                FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
            )
        """))
        
        # Step 3: Copy all data from old table to new table
        self.session.execute(text("""
            INSERT INTO bookings_new (
                id, space_id, user_id, start_time, end_time, license_plate, 
                is_cancelled, deleted_space_info
            )
            SELECT 
                id, space_id, user_id, start_time, end_time, license_plate, 
                is_cancelled, deleted_space_info
            FROM bookings
        """))
        
        # Step 4: Drop old table
        self.session.execute(text("DROP TABLE bookings"))
        
        # Step 5: Rename new table to original name
        self.session.execute(text("ALTER TABLE bookings_new RENAME TO bookings"))
        
        self.session.commit()
        print("✅ User cascade delete migration completed successfully!")
        print("   Users can now be deleted safely - their bookings will have user_id set to NULL")
    
    def down(self) -> None:
        """Rollback the user cascade delete migration."""
        print("🔄 Rolling back user cascade delete migration...")
        
        # Check if there are any bookings with NULL user_id
        result = self.session.execute(text("SELECT COUNT(*) FROM bookings WHERE user_id IS NULL"))
        null_user_bookings = result.fetchone()[0]
        
        if null_user_bookings > 0:
            raise Exception(
                f"Cannot rollback: {null_user_bookings} bookings have NULL user_id. "
                "These would be lost in rollback. Manual cleanup required."
            )
        
        # Step 1: Clean up any previous failed rollback attempts
        try:
            self.session.execute(text("DROP TABLE IF EXISTS bookings_rollback"))
        except:
            pass
        
        # Step 2: Create new table with non-nullable user_id
        self.session.execute(text("""
            CREATE TABLE bookings_rollback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                space_id INTEGER,
                user_id INTEGER NOT NULL,
                start_time DATETIME,
                end_time DATETIME,
                license_plate VARCHAR,
                is_cancelled BOOLEAN DEFAULT 0,
                deleted_space_info VARCHAR,
                FOREIGN KEY(space_id) REFERENCES parking_spaces (id),
                FOREIGN KEY(user_id) REFERENCES users (id)
            )
        """))
        
        # Step 3: Copy data (this will fail if there are NULL user_ids)
        self.session.execute(text("""
            INSERT INTO bookings_rollback (
                id, space_id, user_id, start_time, end_time, license_plate, 
                is_cancelled, deleted_space_info
            )
            SELECT 
                id, space_id, user_id, start_time, end_time, license_plate, 
                is_cancelled, deleted_space_info
            FROM bookings
        """))
        
        # Step 4: Drop old table
        self.session.execute(text("DROP TABLE bookings"))
        
        # Step 5: Rename rollback table
        self.session.execute(text("ALTER TABLE bookings_rollback RENAME TO bookings"))
        
        self.session.commit()
        print("✅ User cascade delete migration rolled back successfully!")
    
    def validate(self) -> bool:
        """Validate that the migration can be applied safely."""
        try:
            # Check that the bookings table exists
            self.session.execute(text("SELECT COUNT(*) FROM bookings LIMIT 1"))
            return True
        except Exception:
            return False
