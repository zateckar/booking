#!/usr/bin/env python3
"""
Migration cleanup utility to handle orphaned or problematic migration records.
"""

import sys
from pathlib import Path
from sqlalchemy.orm import Session
from src.booking.database import SessionLocal
from src.booking.models.migration import SchemaMigration


def get_migration_records() -> list:
    """Get all migration records from the database."""
    session = SessionLocal()
    try:
        records = session.query(SchemaMigration).order_by(SchemaMigration.version).all()
        return records
    finally:
        session.close()


def list_migration_records():
    """List all migration records with their status."""
    print("📋 Migration Records in Database:")
    print("=" * 60)
    
    records = get_migration_records()
    
    if not records:
        print("No migration records found in database.")
        return
    
    for record in records:
        status_icon = {
            "applied": "✅",
            "rolled_back": "🔄",
            "failed": "❌"
        }.get(record.status, "❓")
        
        print(f"{status_icon} {record.version:>3} | {record.status:>12} | {record.description}")
        if record.error_message:
            print(f"      Error: {record.error_message}")
    
    print("=" * 60)
    
    # Summary
    status_counts = {}
    for record in records:
        status_counts[record.status] = status_counts.get(record.status, 0) + 1
    
    print("Summary:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")


def remove_rolled_back_records():
    """Remove all rolled-back migration records from the database."""
    session = SessionLocal()
    try:
        rolled_back = session.query(SchemaMigration).filter(
            SchemaMigration.status == "rolled_back"
        ).all()
        
        if not rolled_back:
            print("No rolled-back migration records found.")
            return
        
        print(f"Found {len(rolled_back)} rolled-back migration record(s):")
        for record in rolled_back:
            print(f"  - {record.version}: {record.description}")
        
        confirm = input("\nDo you want to remove these records? (y/N): ").strip().lower()
        if confirm == 'y':
            for record in rolled_back:
                session.delete(record)
            session.commit()
            print(f"✅ Removed {len(rolled_back)} rolled-back migration record(s).")
        else:
            print("Operation cancelled.")
    
    except Exception as e:
        session.rollback()
        print(f"❌ Error removing records: {e}")
    finally:
        session.close()


def remove_specific_record(version: str):
    """Remove a specific migration record by version."""
    session = SessionLocal()
    try:
        record = session.query(SchemaMigration).filter(
            SchemaMigration.version == version
        ).first()
        
        if not record:
            print(f"Migration record {version} not found.")
            return
        
        print(f"Found migration record:")
        print(f"  Version: {record.version}")
        print(f"  Status: {record.status}")
        print(f"  Description: {record.description}")
        print(f"  Applied at: {record.applied_at}")
        
        if record.error_message:
            print(f"  Error: {record.error_message}")
        
        confirm = input(f"\nDo you want to remove migration record {version}? (y/N): ").strip().lower()
        if confirm == 'y':
            session.delete(record)
            session.commit()
            print(f"✅ Removed migration record {version}.")
        else:
            print("Operation cancelled.")
    
    except Exception as e:
        session.rollback()
        print(f"❌ Error removing record: {e}")
    finally:
        session.close()


def check_missing_files():
    """Check for migration records that don't have corresponding files."""
    from src.booking.migrations.manager import MigrationManager
    
    session = SessionLocal()
    try:
        manager = MigrationManager(session, debug_mode=True)
        
        # Get all records (including rolled back)
        all_records = session.query(SchemaMigration).all()
        
        # Get discovered migrations
        discovered_migrations = manager.discover_migrations()
        discovered_versions = {m.version for m in discovered_migrations}
        
        print("🔍 Checking for missing migration files:")
        print("=" * 50)
        
        missing_files = []
        for record in all_records:
            if record.version not in discovered_versions:
                missing_files.append(record)
        
        if not missing_files:
            print("✅ All migration records have corresponding files.")
        else:
            print(f"❌ Found {len(missing_files)} migration record(s) without files:")
            for record in missing_files:
                status_icon = {
                    "applied": "✅",
                    "rolled_back": "🔄", 
                    "failed": "❌"
                }.get(record.status, "❓")
                print(f"  {status_icon} {record.version} ({record.status}): {record.description}")
        
        print("=" * 50)
        return missing_files
    
    finally:
        session.close()


def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("Migration Cleanup Utility")
        print("=" * 30)
        print("Usage:")
        print("  python cleanup_migrations.py list                  - List all migration records")
        print("  python cleanup_migrations.py check                 - Check for missing files")
        print("  python cleanup_migrations.py clean-rolled-back     - Remove rolled-back records")
        print("  python cleanup_migrations.py remove <version>      - Remove specific record")
        print()
        print("Examples:")
        print("  python cleanup_migrations.py list")
        print("  python cleanup_migrations.py remove 008")
        print("  python cleanup_migrations.py clean-rolled-back")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_migration_records()
    
    elif command == "check":
        check_missing_files()
    
    elif command == "clean-rolled-back":
        remove_rolled_back_records()
    
    elif command == "remove":
        if len(sys.argv) < 3:
            print("❌ Version required for remove command")
            print("Usage: python cleanup_migrations.py remove <version>")
            return
        version = sys.argv[2]
        remove_specific_record(version)
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Run without arguments to see usage.")


if __name__ == "__main__":
    main()
