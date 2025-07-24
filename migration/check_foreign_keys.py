"""
Check foreign key constraints in the bookings table
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.booking.database import SQLALCHEMY_DATABASE_URL

def check_foreign_keys():
    """Check foreign key constraints"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🔍 Checking foreign key constraints...")
        
        # Check foreign keys for bookings table
        result = session.execute(text("PRAGMA foreign_key_list(bookings)"))
        foreign_keys = result.fetchall()
        
        print("\n📋 Foreign keys in bookings table:")
        for fk in foreign_keys:
            print(f"  {fk}")
        
        # Check if foreign keys are enabled
        result = session.execute(text("PRAGMA foreign_keys"))
        fk_enabled = result.fetchone()[0]
        print(f"\n🔧 Foreign keys enabled: {bool(fk_enabled)}")
        
        # Check table schema
        result = session.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name='bookings'"))
        schema = result.fetchone()
        if schema:
            print(f"\n📄 Table creation SQL:\n{schema[0]}")
        
    except Exception as e:
        print(f"❌ Error checking foreign keys: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_foreign_keys()
