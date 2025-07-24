"""
Migration runner for automated database schema management.
"""

import sys
from typing import List, Optional
from sqlalchemy.orm import Session

from .manager import MigrationManager
from .schema_version import SchemaVersionManager, validate_database_compatibility
from ..database import SessionLocal


class MigrationRunner:
    """
    High-level interface for running database migrations.
    
    This class provides the main entry points for migration operations
    and handles database session management.
    """
    
    def __init__(self, session: Optional[Session] = None, migrations_dir: str = None):
        self.session = session
        self.migrations_dir = migrations_dir
        self._own_session = session is None
    
    def _get_session(self) -> Session:
        """Get database session, creating one if needed."""
        if self.session:
            return self.session
        return SessionLocal()
    
    def _close_session(self, session: Session) -> None:
        """Close database session if we created it."""
        if self._own_session:
            session.close()
    
    def run_migrations(self, dry_run: bool = False, target_version: str = None) -> bool:
        """
        Run all pending migrations or up to a specific version.
        
        Args:
            dry_run: If True, validate migrations but don't apply them
            target_version: If specified, run migrations up to this version only
        
        Returns:
            True if all migrations succeeded, False otherwise
        """
        session = self._get_session()
        
        try:
            manager = MigrationManager(session, self.migrations_dir)
            
            print("🔍 Checking migration status...")
            
            # Validate migration integrity first
            validation_errors = manager.validate_migration_integrity()
            if validation_errors:
                print("❌ Migration integrity validation failed:")
                for error in validation_errors:
                    print(f"   - {error}")
                return False
            
            # Get pending migrations
            pending_migrations = manager.get_pending_migrations()
            
            if not pending_migrations:
                print("✅ No pending migrations found. Database is up to date.")
                return True
            
            # Filter migrations if target version is specified
            if target_version:
                filtered_migrations = []
                for migration in pending_migrations:
                    filtered_migrations.append(migration)
                    if migration.version == target_version:
                        break
                pending_migrations = filtered_migrations
            
            print(f"📋 Found {len(pending_migrations)} pending migration(s){'(DRY RUN)' if dry_run else ''}:")
            for migration in pending_migrations:
                temp_instance = migration(session)
                print(f"   - {temp_instance}")
            
            if dry_run:
                print("\n🧪 Running dry-run validation...")
            
            # Apply migrations
            success_count = 0
            for migration_class in pending_migrations:
                if manager.apply_migration(migration_class, dry_run=dry_run):
                    success_count += 1
                else:
                    print(f"❌ Migration process stopped due to failure")
                    return False
            
            if dry_run:
                print(f"\n✅ [DRY RUN] All {success_count} migrations validated successfully")
            else:
                print(f"\n✅ Successfully applied {success_count} migration(s)")
            
            return True
        
        except Exception as e:
            print(f"❌ Migration process failed: {e}")
            return False
        
        finally:
            self._close_session(session)
    
    def rollback_migration(self, version: str) -> bool:
        """
        Rollback a specific migration.
        
        Args:
            version: Version of the migration to rollback
        
        Returns:
            True if successful, False otherwise
        """
        session = self._get_session()
        
        try:
            manager = MigrationManager(session, self.migrations_dir)
            return manager.rollback_migration(version)
        
        except Exception as e:
            print(f"❌ Rollback failed: {e}")
            return False
        
        finally:
            self._close_session(session)
    
    def get_status(self) -> dict:
        """
        Get current migration status.
        
        Returns:
            Dictionary containing migration status information
        """
        session = self._get_session()
        
        try:
            manager = MigrationManager(session, self.migrations_dir)
            return manager.get_migration_status()
        
        finally:
            self._close_session(session)
    
    def print_status(self) -> None:
        """Print detailed migration status to console."""
        session = self._get_session()
        
        try:
            manager = MigrationManager(session, self.migrations_dir)
            
            print("📊 Migration Status Report")
            print("=" * 50)
            
            status = manager.get_migration_status()
            
            print(f"Total migrations: {status['total_migrations']}")
            print(f"Applied: {status['applied_count']}")
            print(f"Pending: {status['pending_count']}")
            
            if status['validation_errors']:
                print(f"\n❌ Validation Errors ({len(status['validation_errors'])}):")
                for error in status['validation_errors']:
                    print(f"   - {error}")
            
            if status['pending_count'] > 0:
                print(f"\n📋 Pending Migrations:")
                pending = manager.get_pending_migrations()
                for migration in pending:
                    temp_instance = migration(session)
                    print(f"   - {temp_instance}")
            
            if status['applied_count'] > 0:
                print(f"\n✅ Applied Migrations:")
                applied = manager.get_applied_migrations()
                for version, migration in sorted(applied.items()):
                    status_icon = "✅" if migration.status == "applied" else "❌"
                    print(f"   {status_icon} {version}: {migration.description} "
                          f"({migration.applied_at.strftime('%Y-%m-%d %H:%M:%S')})")
            
            print("=" * 50)
            
            if status['has_pending']:
                print("⚠️  Database has pending migrations. Run migrations to update schema.")
            elif status['has_errors']:
                print("❌ Database has migration integrity issues. Please review errors above.")
            else:
                print("✅ Database schema is up to date.")
        
        finally:
            self._close_session(session)
    
    def check_schema_compatibility(self) -> tuple[bool, str, dict]:
        """
        Check if database schema is compatible with application requirements.
        
        Returns:
            Tuple of (is_compatible, message, details)
        """
        session = self._get_session()
        
        try:
            manager = MigrationManager(session, self.migrations_dir)
            applied_migrations = manager.get_applied_migrations()
            
            return validate_database_compatibility(applied_migrations)
        
        finally:
            self._close_session(session)
    
    def check_database_ready(self) -> bool:
        """
        Check if database is ready for application use.
        
        Returns:
            True if database is ready (no pending migrations or errors), False otherwise
        """
        try:
            # Check migration status
            status = self.get_status()
            if status['has_pending'] or status['has_errors']:
                return False
            
            # Check schema compatibility
            is_compatible, _, _ = self.check_schema_compatibility()
            return is_compatible
        except Exception:
            return False


# Convenience functions for common operations
def run_migrations(dry_run: bool = False, target_version: str = None) -> bool:
    """Run all pending migrations."""
    runner = MigrationRunner()
    return runner.run_migrations(dry_run=dry_run, target_version=target_version)


def check_database_ready() -> bool:
    """Check if database is ready for application use."""
    runner = MigrationRunner()
    return runner.check_database_ready()


def print_migration_status() -> None:
    """Print migration status to console."""
    runner = MigrationRunner()
    runner.print_status()


if __name__ == "__main__":
    """Command-line interface for migration operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Migration Runner")
    parser.add_argument(
        "command", 
        choices=["run", "status", "rollback", "check"],
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
    
    args = parser.parse_args()
    
    runner = MigrationRunner()
    
    if args.command == "run":
        success = runner.run_migrations(dry_run=args.dry_run, target_version=args.target)
        sys.exit(0 if success else 1)
    
    elif args.command == "status":
        runner.print_status()
    
    elif args.command == "rollback":
        if not args.version:
            print("❌ --version is required for rollback command")
            sys.exit(1)
        success = runner.rollback_migration(args.version)
        sys.exit(0 if success else 1)
    
    elif args.command == "check":
        ready = runner.check_database_ready()
        print("✅ Database is ready" if ready else "❌ Database is not ready")
        sys.exit(0 if ready else 1)
