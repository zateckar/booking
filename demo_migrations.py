#!/usr/bin/env python3
"""
Demonstration script for the database migration system.

This script shows how to create, test, and apply database migrations
in the booking application.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from booking.migrations.runner import MigrationRunner, print_migration_status


def demo_migration_system():
    """Demonstrate the migration system capabilities."""
    
    print("🎯 Database Migration System Demo")
    print("=" * 50)
    
    # 1. Show current status
    print("\n1️⃣ Current Migration Status:")
    print_migration_status()
    
    # 2. Check if database is ready
    print("\n2️⃣ Database Readiness Check:")
    runner = MigrationRunner()
    ready = runner.check_database_ready()
    print(f"   Database ready: {'✅ Yes' if ready else '❌ No'}")
    
    # 3. Show detailed status information
    print("\n3️⃣ Detailed Status Information:")
    status = runner.get_status()
    print(f"   Total migrations: {status['total_migrations']}")
    print(f"   Applied migrations: {status['applied_count']}")
    print(f"   Pending migrations: {status['pending_count']}")
    print(f"   Has validation errors: {'Yes' if status['has_errors'] else 'No'}")
    
    if status['validation_errors']:
        print("   Validation errors:")
        for error in status['validation_errors']:
            print(f"     - {error}")
    
    # 4. Show applied migrations
    if status['applied_count'] > 0:
        print("\n4️⃣ Applied Migrations History:")
        from booking.migrations.manager import MigrationManager
        from booking.database import SessionLocal
        
        session = SessionLocal()
        try:
            manager = MigrationManager(session)
            applied = manager.get_applied_migrations()
            
            for version, migration in sorted(applied.items()):
                status_icon = "✅" if migration.status == "applied" else "❌"
                print(f"   {status_icon} {version}: {migration.description}")
                print(f"      Applied: {migration.applied_at}")
                print(f"      Execution time: {migration.execution_time_ms}ms")
                if migration.error_message:
                    print(f"      Error: {migration.error_message}")
        finally:
            session.close()
    
    print("\n" + "=" * 50)
    print("✅ Migration system demonstration completed!")


if __name__ == "__main__":
    # Set up environment
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "sqlite:///app/data/booking.db"
    
    try:
        demo_migration_system()
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
