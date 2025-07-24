"""
Check the current schema of the bookings table
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.booking.database import SQLALCHEMY_DATABASE_URL

def check_bookings_schema():
    """Check the current bookings table schema"""
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🔍 Checking bookings table schema...")
        
        # Get table info
        result = session.execute(text("PRAGMA table_info(bookings)"))
        columns = result.fetchall()
        
        print("\n📋 Current bookings table columns:")
        for column in columns:
            print(f"  - {column[1]} ({column[2]}{'*' if column[3] else ''}) {'PK' if column[5] else ''}")
        
        print("\n📊 Sample data:")
        result = session.execute(text("SELECT COUNT(*) FROM bookings"))
        count = result.fetchone()[0]
        print(f"  Total bookings: {count}")
        
        if count > 0:
            result = session.execute(text("SELECT * FROM bookings LIMIT 1"))
            sample = result.fetchone()
            if sample:
                print(f"  Sample row: {sample}")
                
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_bookings_schema()
