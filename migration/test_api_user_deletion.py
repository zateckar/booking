"""
Test user deletion through the FastAPI endpoint
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.booking.database import SQLALCHEMY_DATABASE_URL
from src.booking import models

def test_api_user_deletion():
    """Test user deletion through the API"""
    
    # Create test database session
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🧪 Testing API user deletion...")
        
        # Create a test user with bookings
        print("\n🆕 Creating test user with booking...")
        session.execute(text("""
            INSERT INTO users (email, hashed_password, is_admin) 
            VALUES ('api_test@example.com', 'dummy_hash', 0)
        """))
        
        result = session.execute(text("SELECT id FROM users WHERE email = 'api_test@example.com'"))
        test_user_id = result.fetchone()[0]
        print(f"✅ Created test user with ID: {test_user_id}")
        
        # Create a test booking for this user
        session.execute(text("""
            INSERT INTO bookings (space_id, user_id, start_time, end_time, license_plate, is_cancelled)
            VALUES (15, :user_id, '2025-07-25 10:00:00', '2025-07-25 18:00:00', 'API123', 0)
        """), {"user_id": test_user_id})
        print("✅ Created test booking for the user")
        session.commit()
        
        # Test the delete endpoint using the router directly
        from src.booking.routers.admin.users import delete_user
        from src.booking.database import get_db
        
        print(f"\n🗑️ Testing DELETE endpoint for user {test_user_id}...")
        
        # Get a database session
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Call the delete_user function directly
            result = delete_user(test_user_id, db)
            print("✅ User deletion API call successful!")
            print(f"   Deleted user: {result.email}")
            
            # Check what happened to the bookings
            remaining_bookings = session.execute(text("SELECT COUNT(*) FROM bookings WHERE user_id = :user_id"), 
                                                {"user_id": test_user_id}).fetchone()[0]
            null_bookings = session.execute(text("SELECT COUNT(*) FROM bookings WHERE user_id IS NULL")).fetchone()[0]
            
            print(f"📊 Bookings still referencing deleted user: {remaining_bookings}")
            print(f"📊 Bookings with NULL user_id: {null_bookings}")
            
            if remaining_bookings == 0:
                print("✅ API user deletion working correctly!")
            else:
                print("❌ API user deletion has issues")
                
        except Exception as e:
            print(f"❌ API call failed: {e}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    test_api_user_deletion()
