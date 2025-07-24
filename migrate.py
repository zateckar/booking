#!/usr/bin/env python3
"""
Database Migration CLI Tool

This script provides command-line interface for managing database migrations
in the booking application. It can be used during deployments to ensure
database schema is up-to-date.

Usage:
    python migrate.py run                    # Run all pending migrations
    python migrate.py run --dry-run          # Validate migrations without applying
    python migrate.py status                 # Show migration status
    python migrate.py rollback --version 002 # Rollback specific migration
    python migrate.py check                  # Check if database is ready
"""

import sys
import os
import argparse
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from booking.migrations.runner import MigrationRunner


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Database Migration Tool for Booking Application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate.py run                    # Run all pending migrations
  python migrate.py run --dry-run          # Validate migrations without applying
  python migrate.py run --target 002       # Run migrations up to version 002
  python migrate.py status                 # Show detailed migration status
  python migrate.py rollback --version 002 # Rollback migration version 002
  python migrate.py check                  # Check if database is ready

Exit Codes:
  0 - Success
  1 - Error or failure
  2 - Database not ready (for check command)
        """
    )
    
    parser.add_argument(
        "command",
        choices=["run", "status", "rollback", "check", "schema-info", "compatibility"],
        help="Migration command to execute"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run migrations in dry-run mode (validation only)"
    )
    
    parser.add_argument(
        "--target",
        help="Target migration version (for run command)"
    )
    
    parser.add_argument(
        "--version",
        help="Migration version (for rollback command)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Set up environment
    if not os.getenv("DATABASE_URL"):
        # Use default SQLite path if no DATABASE_URL is set
        os.environ["DATABASE_URL"] = "sqlite:///app/data/booking.db"
    
    try:
        runner = MigrationRunner()
        
        if args.command == "run":
            print("🚀 Running database migrations...")
            if args.dry_run:
                print("🧪 DRY RUN MODE - No changes will be applied")
            
            success = runner.run_migrations(
                dry_run=args.dry_run,
                target_version=args.target
            )
            
            if success:
                if args.dry_run:
                    print("\n✅ All migrations validated successfully")
                else:
                    print("\n✅ Database migrations completed successfully")
                sys.exit(0)
            else:
                print("\n❌ Migration process failed")
                sys.exit(1)
        
        elif args.command == "status":
            print("📊 Database Migration Status")
            print("=" * 50)
            runner.print_status()
        
        elif args.command == "rollback":
            if not args.version:
                print("❌ --version is required for rollback command")
                print("   Example: python migrate.py rollback --version 002")
                sys.exit(1)
            
            print(f"🔄 Rolling back migration {args.version}...")
            success = runner.rollback_migration(args.version)
            
            if success:
                print(f"\n✅ Migration {args.version} rolled back successfully")
                sys.exit(0)
            else:
                print(f"\n❌ Failed to rollback migration {args.version}")
                sys.exit(1)
        
        elif args.command == "check":
            ready = runner.check_database_ready()
            
            if ready:
                print("✅ Database is ready - all migrations applied, no errors detected")
                sys.exit(0)
            else:
                status = runner.get_status()
                
                print("❌ Database is not ready:")
                if status['has_pending']:
                    print(f"   - {status['pending_count']} pending migration(s)")
                if status['has_errors']:
                    print(f"   - {len(status['validation_errors'])} validation error(s)")
                
                if args.verbose:
                    print("\nDetailed status:")
                    runner.print_status()
                
                sys.exit(2)
        
        elif args.command == "schema-info":
            from booking.migrations.schema_version import SchemaVersionManager
            
            print("📋 Application Schema Requirements")
            print("=" * 50)
            
            schema_info = SchemaVersionManager.get_schema_info()
            print(f"Required version: {schema_info['required_version']}")
            print(f"Minimum version: {schema_info['minimum_version']}")
            print(f"Maximum version: {schema_info['maximum_version']}")
            print(f"Description: {schema_info['description']}")
            
            print("\n📊 Current Database Status:")
            status = runner.get_status()
            if status['applied_count'] > 0:
                # Get highest applied version
                from booking.migrations.manager import MigrationManager
                from booking.database import SessionLocal
                session = SessionLocal()
                try:
                    manager = MigrationManager(session)
                    applied = manager.get_applied_migrations()
                    current_version = max(applied.keys(), key=lambda x: int(x)) if applied else "none"
                    print(f"Current version: {current_version}")
                finally:
                    session.close()
            else:
                print("Current version: none (no migrations applied)")
        
        elif args.command == "compatibility":
            print("🔍 Database Schema Compatibility Check")
            print("=" * 50)
            
            is_compatible, message, details = runner.check_schema_compatibility()
            
            print(f"Current version: {details.get('current_version', 'unknown')}")
            print(f"Required version: {details.get('required_version')}")
            print(f"Compatible range: {details.get('minimum_version', 'none')}-{details.get('maximum_version', 'none')}")
            print(f"Status: {'✅ Compatible' if is_compatible else '❌ Incompatible'}")
            print(f"Details: {message}")
            
            if not is_compatible:
                issue = details.get('issue')
                if issue == 'database_not_initialized':
                    print("\n💡 Recommendation: Run 'python migrate.py run' to initialize database")
                elif issue == 'failed_migrations':
                    failed = details.get('failed_migrations', [])
                    print(f"\n💡 Recommendation: Fix failed migrations: {failed}")
                else:
                    print("\n💡 Recommendation: Run 'python migrate.py run' to update schema")
                
                sys.exit(1)
            else:
                sys.exit(0)
    
    except KeyboardInterrupt:
        print("\n🛑 Migration process interrupted by user")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
