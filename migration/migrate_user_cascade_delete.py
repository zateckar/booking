"""
Migration to fix user deletion by allowing bookings to have NULL user_id when user is deleted
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.booking.database import SQLALCHEMY_DATABASE_URL

def migrate_user_cascade_delete():
    """
    Migrate to allow user deletion by making user_id nullable in bookings
    and recreating the foreign key with SET NULL on delete
    """
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🔄 Starting user cascade delete migration...")
        
        # Step 0: Clean up any previous failed migration attempts
        try:
            session.execute(text("DROP TABLE IF EXISTS bookings_new"))
            print("🧹 Cleaned up any existing bookings_new table")
        except:
            pass
        
        # Step 1: Create a new bookings table with nullable user_id and proper foreign key
        session.execute(text("""
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
        
        # Step 2: Copy all data from old table to new table
        session.execute(text("""
            INSERT INTO bookings_new (
                id, space_id, user_id, start_time, end_time, license_plate, 
                is_cancelled, deleted_space_info
            )
            SELECT 
                id, space_id, user_id, start_time, end_time, license_plate, 
                is_cancelled, deleted_space_info
            FROM bookings
        """))
        
        # Step 3: Drop old table
        session.execute(text("DROP TABLE bookings"))
        
        # Step 4: Rename new table to original name
        session.execute(text("ALTER TABLE bookings_new RENAME TO bookings"))
        
        session.commit()
        print("✅ User cascade delete migration completed successfully!")
        print("   Users can now be deleted safely - their bookings will have user_id set to NULL")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate_user_cascade_delete()
