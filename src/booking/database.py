import os
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Use the mounted volume directory for database persistence
# Check if DATABASE_URL is set in environment, otherwise use default path
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app/data/booking.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Enable foreign key constraints for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_initial_admin_user():
    """Create initial admin user from environment variables if it doesn't exist"""
    from .models import User  # Import here to avoid circular imports
    
    admin_email = os.getenv("INITIAL_ADMIN_EMAIL")
    admin_password = os.getenv("INITIAL_ADMIN_PASSWORD")
    
    if not admin_email or not admin_password:
        print("⚠️  No initial admin credentials provided via environment variables")
        print("   Set INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD to create default admin user")
        return
    
    db = SessionLocal()
    try:
        # Check if admin user already exists
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if existing_admin:
            print(f"✅ Admin user already exists: {admin_email}")
            return
        
        # Create new admin user
        hashed_password = pwd_context.hash(admin_password)
        admin_user = User(
            email=admin_email,
            hashed_password=hashed_password,
            is_admin=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print(f"✅ Initial admin user created successfully: {admin_email}")
        print("   You can now log in with the provided credentials")
        
    except Exception as e:
        print(f"❌ Failed to create initial admin user: {e}")
        db.rollback()
    finally:
        db.close()


def create_db_and_tables():
    """Create database tables, run migrations, and create initial admin user"""
    # First, create base tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Run any pending migrations and check schema compatibility
    from .migrations.runner import run_migrations, MigrationRunner
    from .migrations.schema_version import SchemaVersionManager
    
    try:
        print("🔍 Checking database schema compatibility...")
        
        # Check schema requirements
        runner = MigrationRunner()
        is_compatible, message, details = runner.check_schema_compatibility()
        
        if not is_compatible:
            print(f"⚠️  Schema compatibility check: {message}")
            print(f"   Current version: {details.get('current_version', 'unknown')}")
            print(f"   Required version: {details.get('required_version')}")
            
            if details.get('issue') == 'database_not_initialized':
                print("🔧 Database not initialized. Running migrations...")
            elif details.get('issue') == 'failed_migrations':
                print("❌ Database has failed migrations. Manual intervention required.")
                return
            else:
                print("🔧 Running migrations to update schema...")
        
        # Run pending migrations
        print("🔍 Checking for pending migrations...")
        if not run_migrations():
            print("⚠️  Some migrations failed. Please check the logs.")
            return
        
        # Verify schema compatibility after migrations
        is_compatible, message, details = runner.check_schema_compatibility()
        if is_compatible:
            print(f"✅ Database schema is compatible: {message}")
        else:
            print(f"❌ Database schema compatibility issue: {message}")
            print("⚠️  Application may not function correctly!")
            
    except Exception as e:
        print(f"⚠️  Migration check failed: {e}")
    
    # Create initial admin user after migrations
    create_initial_admin_user()
