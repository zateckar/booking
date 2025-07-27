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
    
    def __init__(self, session: Optional[Session] = None, migrations_dir: str = None, debug_mode: bool = False):
        self.session = session
        self.migrations_dir = migrations_dir
        self.debug_mode = debug_mode
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
            manager = MigrationManager(session, self.migrations_dir, debug_mode=self.debug_mode)
            
            print("🔍 Checking migration status...")
            
            # Validate migration integrity with enhanced error handling
            validation_errors = manager.validate_migration_integrity()
            discovery_errors = manager.get_discovery_errors()
            discovery_warnings = manager.get_discovery_warnings()
            
            # Handle discovery warnings
            if discovery_warnings:
                print("⚠️  Migration discovery warnings:")
                for warning in discovery_warnings:
                    print(f"   - {warning}")
            
            # Handle discovery errors with enhanced reporting
            if discovery_errors:
                print("❌ Migration discovery errors detected:")
                for error in discovery_errors:
                    # Use the enhanced error message formatting
                    print(f"   - {error.get_actionable_message()}")
                    
                    # Show import attempts if available and in debug mode
                    if hasattr(error, 'import_attempts') and error.import_attempts and len(error.import_attempts) > 0:
                        print(f"     Import attempts made: {len(error.import_attempts)}")
                        for attempt in error.import_attempts:
                            status = "✓" if attempt.success else "✗"
                            print(f"       {status} {attempt.strategy.value}: {attempt.error_message or 'Success'}")
                
                # Classify errors by severity
                critical_errors = [e for e in discovery_errors if e.severity == "ERROR"]
                warning_errors = [e for e in discovery_errors if e.severity == "WARNING"]
                
                if critical_errors:
                    print(f"\n❌ Found {len(critical_errors)} critical discovery error(s). Cannot proceed.")
                    print("   Consider running with debug mode enabled for more detailed diagnostics.")
                    return False
                elif warning_errors:
                    print(f"\n⚠️  Found {len(warning_errors)} discovery warning(s). Proceeding with caution.")
            
            # Handle validation errors with enhanced classification
            if validation_errors:
                print("❌ Migration integrity validation failed:")
                for error in validation_errors:
                    print(f"   - {error}")
                
                # Check if these are just missing file errors vs. other validation issues
                missing_file_errors = [e for e in validation_errors if "not found" in str(e).lower()]
                other_errors = [e for e in validation_errors if "not found" not in str(e).lower()]
                
                if missing_file_errors and not other_errors:
                    print("\n💡 All validation errors appear to be missing migration files.")
                    print("   This may indicate a migration discovery issue rather than data corruption.")
                
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
            
            print(f"📋 Found {len(pending_migrations)} pending migration(s){' (DRY RUN)' if dry_run else ''}:")
            for migration in pending_migrations:
                try:
                    temp_instance = migration(session)
                    print(f"   - {temp_instance}")
                except Exception as e:
                    print(f"   - {migration.version}: Failed to create instance - {e}")
                    return False
            
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
            manager = MigrationManager(session, self.migrations_dir, debug_mode=self.debug_mode)
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
            manager = MigrationManager(session, self.migrations_dir, debug_mode=self.debug_mode)
            return manager.get_migration_status()
        
        finally:
            self._close_session(session)
    
    def print_status(self) -> None:
        """Print detailed migration status to console with enhanced error reporting."""
        session = self._get_session()
        
        try:
            manager = MigrationManager(session, self.migrations_dir, debug_mode=self.debug_mode)
            
            print("📊 Migration Status Report")
            print("=" * 50)
            
            status = manager.get_migration_status()
            
            print(f"Total migrations: {status['total_migrations']}")
            print(f"Applied: {status['applied_count']}")
            print(f"Pending: {status['pending_count']}")
            
            # Display discovery errors with enhanced information
            if status['discovery_errors']:
                print(f"\n❌ Discovery Errors ({len(status['discovery_errors'])}):")
                for error_dict in status['discovery_errors']:
                    print(f"   - {error_dict['version']} ({error_dict['type']}): {error_dict['message']}")
                    if error_dict.get('file_path'):
                        print(f"     File: {error_dict['file_path']}")
                    if error_dict.get('import_attempts', 0) > 0:
                        print(f"     Import attempts: {error_dict['import_attempts']}")
                
                # Get full discovery errors for enhanced reporting
                discovery_errors = manager.get_discovery_errors()
                if discovery_errors:
                    print("\n💡 Detailed Error Analysis:")
                    error_types = {}
                    for error in discovery_errors:
                        error_type = error.error_type
                        error_types[error_type] = error_types.get(error_type, 0) + 1
                    
                    for error_type, count in error_types.items():
                        print(f"   - {error_type}: {count} occurrence(s)")
                    
                    # Show actionable recommendations
                    critical_errors = [e for e in discovery_errors if e.severity == "ERROR"]
                    if critical_errors and hasattr(critical_errors[0], 'suggested_fixes'):
                        print("\n🔧 Suggested Actions:")
                        all_fixes = set()
                        for error in critical_errors:
                            if error.suggested_fixes:
                                all_fixes.update(error.suggested_fixes)
                        
                        for i, fix in enumerate(sorted(all_fixes), 1):
                            print(f"   {i}. {fix}")
            
            # Display discovery warnings
            if status['discovery_warnings']:
                print(f"\n⚠️  Discovery Warnings ({len(status['discovery_warnings'])}):")
                for warning in status['discovery_warnings']:
                    print(f"   - {warning}")
            
            # Display validation errors with enhanced classification
            if status['validation_errors']:
                print(f"\n❌ Validation Errors ({len(status['validation_errors'])}):")
                
                # Classify validation errors
                missing_file_errors = []
                checksum_errors = []
                other_errors = []
                
                for error in status['validation_errors']:
                    error_str = str(error)
                    if "not found" in error_str.lower():
                        missing_file_errors.append(error)
                    elif "checksum" in error_str.lower() or "mismatch" in error_str.lower():
                        checksum_errors.append(error)
                    else:
                        other_errors.append(error)
                
                if missing_file_errors:
                    print(f"   📁 Missing Migration Files ({len(missing_file_errors)}):")
                    for error in missing_file_errors:
                        print(f"     - {error}")
                
                if checksum_errors:
                    print(f"   🔍 Checksum Mismatches ({len(checksum_errors)}):")
                    for error in checksum_errors:
                        print(f"     - {error}")
                
                if other_errors:
                    print(f"   ❓ Other Validation Issues ({len(other_errors)}):")
                    for error in other_errors:
                        print(f"     - {error}")
            
            if status['pending_count'] > 0:
                print(f"\n📋 Pending Migrations:")
                pending = manager.get_pending_migrations()
                for migration in pending:
                    try:
                        temp_instance = migration(session)
                        print(f"   - {temp_instance}")
                    except Exception as e:
                        print(f"   - {migration.version}: Failed to create instance - {e}")
            
            if status['applied_count'] > 0:
                print(f"\n✅ Applied Migrations:")
                applied = manager.get_applied_migrations()
                for version, migration in sorted(applied.items()):
                    status_icon = "✅" if migration.status == "applied" else "❌"
                    print(f"   {status_icon} {version}: {migration.description} "
                          f"({migration.applied_at.strftime('%Y-%m-%d %H:%M:%S')})")
            
            print("=" * 50)
            
            # Enhanced status summary with actionable guidance
            if status['has_pending']:
                print("⚠️  Database has pending migrations. Run migrations to update schema.")
            elif status['has_errors'] or status['discovery_errors']:
                print("❌ Database has migration issues. Please review errors above.")
                if status['discovery_errors']:
                    print("   💡 Run with debug mode enabled for detailed diagnostics:")
                    print("      python -m booking.migrations.runner --debug status")
                    print("   🔧 Generate diagnostic report:")
                    print("      python -c \"from booking.migrations.manager import MigrationManager; print(MigrationManager().generate_diagnostic_report())\"")
            elif status['has_warnings']:
                print("⚠️  Database has migration warnings but is functional.")
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
            manager = MigrationManager(session, self.migrations_dir, debug_mode=self.debug_mode)
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
    
    def generate_diagnostic_report(self) -> dict:
        """
        Generate a comprehensive diagnostic report for troubleshooting migration issues.
        
        Returns:
            Dictionary containing detailed diagnostic information
        """
        session = self._get_session()
        
        try:
            manager = MigrationManager(session, self.migrations_dir, debug_mode=True)
            
            # Trigger discovery to populate error tracking
            manager.discover_migrations()
            
            return manager.generate_diagnostic_report()
        
        finally:
            self._close_session(session)
    
    def print_diagnostic_report(self) -> None:
        """Print a comprehensive diagnostic report to console."""
        import json
        
        print("🔍 Migration Diagnostic Report")
        print("=" * 60)
        
        report = self.generate_diagnostic_report()
        
        print(f"Generated: {report['timestamp']}")
        env = report['environment']
        print(f"Environment: Python {env.get('python_version', 'Unknown')}")
        print(f"Migrations Directory: {env.get('migrations_dir', 'Unknown')}")
        print(f"Working Directory: {env.get('current_working_dir', 'Unknown')}")
        
        summary = report['discovery_summary']
        print(f"\nDiscovery Summary:")
        print(f"  Total Errors: {summary['total_errors']}")
        print(f"  Total Warnings: {summary['total_warnings']}")
        
        if summary['error_types']:
            print(f"\nError Types:")
            for error_type, count in summary['error_types'].items():
                print(f"  - {error_type}: {count}")
        
        if summary['import_strategy_success_rates']:
            print(f"\nImport Strategy Success Rates:")
            for strategy, stats in summary['import_strategy_success_rates'].items():
                print(f"  - {strategy}: {stats['success_rate_percent']}% "
                      f"({stats['success_count']}/{stats['success_count'] + stats['failure_count']})")
        
        if report['errors']:
            print(f"\nDetailed Errors:")
            for error in report['errors']:
                print(f"  📁 {error['version']} ({error['type']}):")
                print(f"     Message: {error['message']}")
                if error.get('file_path'):
                    print(f"     File: {error['file_path']}")
                if error.get('suggested_fixes'):
                    print(f"     Suggested Fixes:")
                    for fix in error['suggested_fixes']:
                        print(f"       • {fix}")
        
        if report['warnings']:
            print(f"\nWarnings:")
            for warning in report['warnings']:
                print(f"  ⚠️  {warning}")
        
        if report['actionable_recommendations']:
            print(f"\n🔧 Actionable Recommendations:")
            for i, recommendation in enumerate(report['actionable_recommendations'], 1):
                print(f"  {i}. {recommendation}")
        
        print("=" * 60)


# Convenience functions for common operations
def run_migrations(dry_run: bool = False, target_version: str = None, debug_mode: bool = False) -> bool:
    """Run all pending migrations."""
    runner = MigrationRunner(debug_mode=debug_mode)
    return runner.run_migrations(dry_run=dry_run, target_version=target_version)


def check_database_ready(debug_mode: bool = False) -> bool:
    """Check if database is ready for application use."""
    runner = MigrationRunner(debug_mode=debug_mode)
    return runner.check_database_ready()


def print_migration_status(debug_mode: bool = False) -> None:
    """Print migration status to console."""
    runner = MigrationRunner(debug_mode=debug_mode)
    runner.print_status()


def print_diagnostic_report() -> None:
    """Print comprehensive diagnostic report to console."""
    runner = MigrationRunner(debug_mode=True)
    runner.print_diagnostic_report()


if __name__ == "__main__":
    """Command-line interface for migration operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Migration Runner")
    parser.add_argument(
        "command", 
        choices=["run", "status", "rollback", "check", "diagnose"],
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
        "--debug", 
        action="store_true",
        help="Enable debug mode for detailed diagnostics"
    )
    
    args = parser.parse_args()
    
    runner = MigrationRunner(debug_mode=args.debug)
    
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
    
    elif args.command == "diagnose":
        runner.print_diagnostic_report()
