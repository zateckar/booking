"""
Test user deletion with foreign keys properly enabled
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.booking.database import SQLALCHEMY_DATABASE_URL

def test_user_deletion_with_fk():
    """Test user deletion with foreign keys enabled"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🧪 Testing user deletion with foreign keys enabled...")
        
        # Enable foreign keys for this session
        session.execute(text("PRAGMA foreign_keys = ON"))
        
        # Verify foreign keys are enabled
        result = session.execute(text("PRAGMA foreign_keys"))
        fk_enabled = result.fetchone()[0]
        print(f"🔧 Foreign keys enabled: {bool(fk_enabled)}")
        
        if not fk_enabled:
            print("❌ Failed to enable foreign keys")
            return
        
        # Check current users and their bookings
        print("\n📋 Current users and bookings:")
        result = session.execute(text("""
            SELECT u.id, u.email, COUNT(b.id) as booking_count
            FROM users u 
            LEFT JOIN bookings b ON u.id = b.user_id 
            GROUP BY u.id, u.email
            ORDER BY u.id
        """))
        users = result.fetchall()
        
        for user in users:
            print(f"  User {user[0]}: {user[1]} ({user[2]} bookings)")
        
        # Since user 1 was already deleted, let's create a test user with bookings
        print("\n🆕 Creating a test user...")
        session.execute(text("""
            INSERT INTO users (email, hashed_password, is_admin) 
            VALUES ('test@example.com', 'dummy_hash', 0)
        """))
        
        result = session.execute(text("SELECT id FROM users WHERE email = 'test@example.com'"))
        test_user_id = result.fetchone()[0]
        print(f"✅ Created test user with ID: {test_user_id}")
        
        # Create a test booking for this user
        session.execute(text("""
            INSERT INTO bookings (space_id, user_id, start_time, end_time, license_plate, is_cancelled)
            VALUES (15, :user_id, '2025-07-25 09:00:00', '2025-07-25 17:00:00', 'TEST123', 0)
        """), {"user_id": test_user_id})
        print("✅ Created test booking for the user")
        
        # Check bookings before deletion
        result = session.execute(text("SELECT COUNT(*) FROM bookings WHERE user_id = :user_id"), 
                                {"user_id": test_user_id})
        bookings_before = result.fetchone()[0]
        print(f"📊 Bookings for test user before deletion: {bookings_before}")
        
        # Attempt to delete the user
        print(f"\n🗑️ Attempting to delete test user {test_user_id}...")
        result = session.execute(text("DELETE FROM users WHERE id = :user_id"), 
                                {"user_id": test_user_id})
        
        if result.rowcount > 0:
            print("✅ User deleted successfully!")
            
            # Check what happened to the bookings
            result = session.execute(text("SELECT COUNT(*) FROM bookings WHERE user_id IS NULL"))
            null_bookings = result.fetchone()[0]
            
            result = session.execute(text("SELECT COUNT(*) FROM bookings WHERE user_id = :user_id"), 
                                    {"user_id": test_user_id})
            remaining_bookings = result.fetchone()[0]
            
            print(f"📊 Bookings with NULL user_id: {null_bookings}")
            print(f"📊 Bookings still referencing deleted user: {remaining_bookings}")
            
            if remaining_bookings == 0:
                print("✅ Foreign key constraint working correctly - bookings updated to NULL")
            else:
                print("❌ Some bookings still reference the deleted user")
            
            session.commit()
        else:
            print("❌ User deletion failed - no rows affected")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    test_user_deletion_with_fk()
