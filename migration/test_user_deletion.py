"""
Test user deletion functionality after migration
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.booking.database import SQLALCHEMY_DATABASE_URL

def test_user_deletion():
    """Test that users can now be deleted safely"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🧪 Testing user deletion functionality...")
        
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
        
        # Find user with bookings to test deletion
        test_user_id = None
        for user in users:
            if user[2] > 0:  # Has bookings
                test_user_id = user[0]
                print(f"\n🎯 Will test deletion of user {test_user_id} who has {user[2]} bookings")
                break
        
        if test_user_id is None:
            print("❌ No users with bookings found to test deletion")
            return
        
        # Check bookings before deletion
        result = session.execute(text("SELECT COUNT(*) FROM bookings WHERE user_id = :user_id"), 
                                {"user_id": test_user_id})
        bookings_before = result.fetchone()[0]
        print(f"📊 Bookings for user {test_user_id} before deletion: {bookings_before}")
        
        # Attempt to delete the user
        print(f"\n🗑️ Attempting to delete user {test_user_id}...")
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
    test_user_deletion()
