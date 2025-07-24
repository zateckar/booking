"""
Restore users that were deleted during testing
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.booking.database import SQLALCHEMY_DATABASE_URL, pwd_context

def restore_deleted_users():
    """Restore users deleted during testing"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🔄 Restoring deleted users...")
        
        # Check current users
        result = session.execute(text("SELECT id, email FROM users ORDER BY id"))
        current_users = result.fetchall()
        print("\n📋 Current users:")
        for user in current_users:
            print(f"  User {user[0]}: {user[1]}")
        
        # Restore the initial admin user (ID 1) if missing
        admin_exists = any(user[0] == 1 for user in current_users)
        if not admin_exists:
            print("\n🔄 Restoring initial admin user (ID 1)...")
            # Use environment variables if available, otherwise use defaults
            admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com")
            admin_password = os.getenv("INITIAL_ADMIN_PASSWORD", "admin")
            hashed_password = pwd_context.hash(admin_password)
            
            session.execute(text("""
                INSERT INTO users (id, email, hashed_password, is_admin) 
                VALUES (1, :email, :password, 1)
            """), {"email": admin_email, "password": hashed_password})
            print(f"✅ Restored admin user: {admin_email}")
        else:
            print("✅ Initial admin user already exists")
        
        # Check if we need to restore the bookings' user_id references
        result = session.execute(text("SELECT COUNT(*) FROM bookings WHERE user_id IS NULL"))
        null_bookings = result.fetchone()[0]
        
        if null_bookings > 0:
            print(f"\n📊 Found {null_bookings} bookings with NULL user_id")
            
            # Try to restore bookings to the admin user if they were orphaned
            result = session.execute(text("SELECT id FROM users WHERE is_admin = 1 LIMIT 1"))
            admin_user = result.fetchone()
            
            if admin_user:
                admin_id = admin_user[0]
                print(f"🔄 Reassigning orphaned bookings to admin user (ID {admin_id})...")
                
                session.execute(text("""
                    UPDATE bookings 
                    SET user_id = :admin_id 
                    WHERE user_id IS NULL
                """), {"admin_id": admin_id})
                
                print(f"✅ Reassigned {null_bookings} orphaned bookings to admin user")
        
        session.commit()
        
        # Show final user list
        result = session.execute(text("SELECT id, email, is_admin FROM users ORDER BY id"))
        final_users = result.fetchall()
        print("\n📋 Final user list:")
        for user in final_users:
            admin_flag = " (ADMIN)" if user[2] else ""
            print(f"  User {user[0]}: {user[1]}{admin_flag}")
        
        print("\n✅ User restoration completed successfully!")
        
    except Exception as e:
        print(f"❌ Restoration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    restore_deleted_users()
