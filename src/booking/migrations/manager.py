"""
Migration manager for database schema changes.
"""

import os
import sys
import importlib
import time
from pathlib import Path
from typing import List, Dict, Optional, Type
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models.migration import SchemaMigration
from .base import BaseMigration


class MigrationManager:
    """
    Manages database migrations including discovery, tracking, and execution.
    """
    
    def __init__(self, session: Session, migrations_dir: str = None):
        self.session = session
        self.migrations_dir = migrations_dir or self._get_default_migrations_dir()
        self._ensure_migrations_table()
    
    def _get_default_migrations_dir(self) -> str:
        """Get the default migrations directory."""
        current_dir = Path(__file__).parent
        return str(current_dir / "scripts")
    
    def _ensure_migrations_table(self) -> None:
        """Ensure the schema_migrations table exists."""
        try:
            # Try to query the table to see if it exists
            self.session.execute(text("SELECT COUNT(*) FROM schema_migrations LIMIT 1"))
        except Exception:
            # Table doesn't exist, create it
            from ..models import SchemaMigration
            from ..database import Base, engine
            SchemaMigration.__table__.create(engine, checkfirst=True)
            self.session.commit()
    
    def discover_migrations(self) -> List[Type[BaseMigration]]:
        """
        Discover all migration classes in the migrations directory.
        Returns migrations sorted by version.
        """
        migrations = []
        migrations_path = Path(self.migrations_dir)
        
        if not migrations_path.exists():
            return migrations
        
        # Add migrations directory to Python path
        if str(migrations_path) not in sys.path:
            sys.path.insert(0, str(migrations_path))
        
        try:
            # Find all Python files that look like migrations
            for file_path in migrations_path.glob("*.py"):
                if file_path.name.startswith("__"):
                    continue
                
                module_name = file_path.stem
                try:
                    module = importlib.import_module(module_name)
                    
                    # Look for migration classes in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, BaseMigration) and 
                            attr != BaseMigration and 
                            hasattr(attr, 'version') and 
                            attr.version):
                            migrations.append(attr)
                
                except Exception as e:
                    print(f"⚠️  Warning: Could not load migration from {file_path}: {e}")
        
        finally:
            # Clean up sys.path
            if str(migrations_path) in sys.path:
                sys.path.remove(str(migrations_path))
        
        # Sort by version
        migrations.sort(key=lambda m: m.version)
        return migrations
    
    def get_applied_migrations(self) -> Dict[str, SchemaMigration]:
        """Get all applied migrations from the database."""
        applied = self.session.query(SchemaMigration).all()
        return {migration.version: migration for migration in applied}
    
    def get_pending_migrations(self) -> List[Type[BaseMigration]]:
        """Get all migrations that haven't been applied yet."""
        all_migrations = self.discover_migrations()
        applied_migrations = self.get_applied_migrations()
        
        pending = []
        for migration_class in all_migrations:
            if migration_class.version not in applied_migrations:
                pending.append(migration_class)
        
        return pending
    
    def validate_migration_integrity(self) -> List[str]:
        """
        Validate that applied migrations haven't been modified.
        Returns a list of validation errors.
        """
        errors = []
        all_migrations = self.discover_migrations()
        applied_migrations = self.get_applied_migrations()
        
        # Create a lookup for migration classes by version
        migration_classes = {m.version: m for m in all_migrations}
        
        for version, applied_migration in applied_migrations.items():
            if version not in migration_classes:
                errors.append(f"Applied migration {version} not found in migration files")
                continue
            
            migration_class = migration_classes[version]
            # Create temporary instance to get checksum
            temp_instance = migration_class(self.session)
            current_checksum = temp_instance.get_checksum()
            
            if current_checksum != applied_migration.checksum:
                errors.append(
                    f"Migration {version} has been modified after application "
                    f"(checksum mismatch: {applied_migration.checksum} != {current_checksum})"
                )
        
        return errors
    
    def apply_migration(self, migration_class: Type[BaseMigration], dry_run: bool = False) -> bool:
        """
        Apply a single migration.
        
        Args:
            migration_class: The migration class to apply
            dry_run: If True, validate but don't actually apply the migration
        
        Returns:
            True if successful, False otherwise
        """
        migration = migration_class(self.session)
        
        print(f"📝 {'[DRY RUN] ' if dry_run else ''}Applying migration {migration}")
        
        # Validate migration
        if not migration.validate():
            print(f"❌ Migration validation failed: {migration.version}")
            return False
        
        if dry_run:
            print(f"✅ [DRY RUN] Migration {migration.version} validation passed")
            return True
        
        start_time = time.time()
        error_message = None
        
        try:
            # Execute the migration
            migration.up()
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Record the migration as applied
            migration_record = SchemaMigration(
                version=migration.version,
                description=migration.description,
                checksum=migration.get_checksum(),
                class_name=migration.__class__.__name__,
                execution_time_ms=execution_time_ms,
                status="applied"
            )
            
            self.session.add(migration_record)
            self.session.commit()
            
            print(f"✅ Migration {migration.version} applied successfully ({execution_time_ms}ms)")
            return True
        
        except Exception as e:
            error_message = str(e)
            print(f"❌ Migration {migration.version} failed: {error_message}")
            
            # Record the failed migration
            try:
                execution_time_ms = int((time.time() - start_time) * 1000)
                migration_record = SchemaMigration(
                    version=migration.version,
                    description=migration.description,
                    checksum=migration.get_checksum(),
                    class_name=migration.__class__.__name__,
                    execution_time_ms=execution_time_ms,
                    status="failed",
                    error_message=error_message
                )
                
                self.session.add(migration_record)
                self.session.commit()
            except Exception as record_error:
                print(f"⚠️  Could not record failed migration: {record_error}")
                self.session.rollback()
            
            return False
    
    def rollback_migration(self, version: str) -> bool:
        """
        Rollback a specific migration.
        
        Args:
            version: Version of the migration to rollback
        
        Returns:
            True if successful, False otherwise
        """
        # Find the migration class
        all_migrations = self.discover_migrations()
        migration_class = None
        
        for m in all_migrations:
            if m.version == version:
                migration_class = m
                break
        
        if not migration_class:
            print(f"❌ Migration {version} not found")
            return False
        
        # Check if migration is applied
        applied_migration = self.session.query(SchemaMigration).filter(
            SchemaMigration.version == version
        ).first()
        
        if not applied_migration:
            print(f"❌ Migration {version} is not applied")
            return False
        
        if applied_migration.status != "applied":
            print(f"❌ Migration {version} is not in applied status (current: {applied_migration.status})")
            return False
        
        migration = migration_class(self.session)
        
        print(f"🔄 Rolling back migration {migration}")
        
        start_time = time.time()
        
        try:
            # Execute rollback
            migration.down()
            
            # Update migration record
            execution_time_ms = int((time.time() - start_time) * 1000)
            applied_migration.status = "rolled_back"
            applied_migration.execution_time_ms = execution_time_ms
            
            self.session.commit()
            
            print(f"✅ Migration {version} rolled back successfully ({execution_time_ms}ms)")
            return True
        
        except NotImplementedError:
            print(f"❌ Migration {version} does not support rollback")
            return False
        
        except Exception as e:
            error_message = str(e)
            print(f"❌ Rollback of migration {version} failed: {error_message}")
            
            # Update with error
            applied_migration.error_message = error_message
            self.session.commit()
            
            return False
    
    def get_migration_status(self) -> Dict:
        """Get overall migration status information."""
        all_migrations = self.discover_migrations()
        applied_migrations = self.get_applied_migrations()
        pending_migrations = self.get_pending_migrations()
        validation_errors = self.validate_migration_integrity()
        
        return {
            'total_migrations': len(all_migrations),
            'applied_count': len(applied_migrations),
            'pending_count': len(pending_migrations),
            'validation_errors': validation_errors,
            'has_pending': len(pending_migrations) > 0,
            'has_errors': len(validation_errors) > 0
        }
