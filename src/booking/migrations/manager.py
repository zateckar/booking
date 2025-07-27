"""
Migration manager for database schema changes.
"""

import os
import sys
import importlib
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Type, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models.migration import SchemaMigration
from .base import BaseMigration
from .discovery import (
    ModuleLoader, ClassExtractor, ValidationHelper,
    MigrationLoadingContext, MigrationDiscoveryError,
    ValidationResult, ImportStrategy
)


class MigrationManager:
    """
    Manages database migrations including discovery, tracking, and execution.
    """
    
    def __init__(self, session: Session, migrations_dir: str = None, debug_mode: bool = False):
        self.session = session
        self.migrations_dir = migrations_dir or self._get_default_migrations_dir()
        self.debug_mode = debug_mode
        self.logger = logging.getLogger(__name__)
        
        # Initialize discovery utilities
        self.loading_context = MigrationLoadingContext(
            migrations_dir=self.migrations_dir,
            python_path=sys.path.copy(),
            import_strategies=[
                ImportStrategy.RELATIVE_IMPORT,
                ImportStrategy.ABSOLUTE_IMPORT,
                ImportStrategy.DIRECT_FILE_LOADING,
                ImportStrategy.SYSPATH_MANIPULATION
            ],
            debug_mode=debug_mode
        )
        
        self.module_loader = ModuleLoader(self.loading_context)
        self.class_extractor = ClassExtractor(debug_mode, self.logger)
        self.validation_helper = ValidationHelper(debug_mode, self.logger)
        
        # Error tracking
        self.discovery_errors: List[MigrationDiscoveryError] = []
        self.discovery_warnings: List[str] = []
        
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
    
    def _load_migration_module(self, file_path: Path) -> Optional[any]:
        """
        Load a migration module using multiple fallback strategies.
        
        This method implements robust module loading with detailed error tracking
        and recovery mechanisms to handle different deployment environments.
        
        Args:
            file_path: Path to the migration file
            
        Returns:
            Loaded module or None if all strategies failed
        """
        module_name = file_path.stem
        
        self.logger.debug(f"Attempting to load migration module: {module_name} from {file_path}")
        
        # Use the ModuleLoader with fallback strategies
        module, import_attempts = self.module_loader.load_module(file_path)
        
        if module is not None:
            self.logger.debug(f"Successfully loaded migration module: {module_name}")
            return module
        
        # All import strategies failed - create detailed error
        from .discovery import ValidationErrorType
        error = MigrationDiscoveryError(
            version=module_name,  # Use filename as version for now
            error_type=ValidationErrorType.MODULE_IMPORT_FAILED.value,
            error_message=f"Failed to import migration module {module_name} using all available strategies",
            file_path=str(file_path),
            import_attempts=import_attempts
        )
        
        self.discovery_errors.append(error)
        
        # Log detailed information about each failed attempt
        self.logger.error(f"Failed to load migration module {module_name}:")
        for attempt in import_attempts:
            self.logger.error(f"  - {attempt.strategy.value}: {attempt.error_message}")
            if self.debug_mode and attempt.stack_trace:
                self.logger.debug(f"    Stack trace: {attempt.stack_trace}")
        
        return None
    
    def _extract_migration_classes_from_module(self, module: any, file_path: Path) -> List[Type[BaseMigration]]:
        """
        Extract migration classes from a loaded module with error handling.
        
        Args:
            module: The loaded module
            file_path: Path to the migration file
            
        Returns:
            List of discovered migration classes
        """
        migration_classes, warnings = self.class_extractor.extract_migration_classes(module, file_path)
        
        # Add warnings to our tracking
        self.discovery_warnings.extend(warnings)
        
        # Validate each discovered migration class
        validated_classes = []
        for migration_class in migration_classes:
            validation_result = self.validation_helper.validate_migration_structure(migration_class)
            
            if validation_result.is_valid:
                validated_classes.append(migration_class)
                self.logger.debug(f"Validated migration class: {migration_class.__name__}")
            else:
                # Add validation errors to our tracking
                self.discovery_errors.extend(validation_result.errors)
                self.logger.warning(f"Migration class {migration_class.__name__} failed validation")
            
            # Add validation warnings
            self.discovery_warnings.extend(validation_result.warnings)
        
        return validated_classes
    
    def _handle_migration_discovery_error(self, file_path: Path, error: Exception) -> None:
        """
        Handle and track migration discovery errors with detailed information.
        
        Args:
            file_path: Path to the migration file that caused the error
            error: The exception that occurred
        """
        import traceback
        
        from .discovery import ValidationErrorType
        error_info = MigrationDiscoveryError(
            version=file_path.stem,
            error_type=ValidationErrorType.DISCOVERY_ERROR.value,
            error_message=f"Unexpected error during migration discovery: {str(error)}",
            file_path=str(file_path),
            stack_trace=traceback.format_exc() if self.debug_mode else None
        )
        
        self.discovery_errors.append(error_info)
        
        self.logger.error(f"Migration discovery error for {file_path}: {str(error)}")
        if self.debug_mode:
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
    
    def _reset_discovery_state(self) -> None:
        """Reset discovery error and warning tracking."""
        self.discovery_errors.clear()
        self.discovery_warnings.clear()
    
    def get_discovery_errors(self) -> List[MigrationDiscoveryError]:
        """Get all discovery errors from the last discovery operation."""
        return self.discovery_errors.copy()
    
    def get_discovery_warnings(self) -> List[str]:
        """Get all discovery warnings from the last discovery operation."""
        return self.discovery_warnings.copy()
    
    def generate_diagnostic_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive diagnostic report for troubleshooting migration issues.
        
        Returns:
            Dictionary containing detailed diagnostic information
        """
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "environment": self.loading_context.get_diagnostic_info(),
            "discovery_summary": {
                "total_errors": len(self.discovery_errors),
                "total_warnings": len(self.discovery_warnings),
                "error_types": {},
                "import_strategy_success_rates": {}
            },
            "errors": [],
            "warnings": self.discovery_warnings.copy(),
            "actionable_recommendations": []
        }
        
        # Analyze error types
        error_type_counts = {}
        import_attempts_by_strategy = {}
        
        for error in self.discovery_errors:
            error_type = error.error_type
            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1
            
            # Add detailed error information
            error_detail = {
                "version": error.version,
                "type": error.error_type,
                "message": error.error_message,
                "file_path": error.file_path,
                "suggested_fixes": error.suggested_fixes,
                "diagnostic_info": error.diagnostic_info,
                "severity": error.severity
            }
            
            # Include import attempts if available
            if error.import_attempts:
                error_detail["import_attempts"] = []
                for attempt in error.import_attempts:
                    strategy = attempt.strategy.value
                    if strategy not in import_attempts_by_strategy:
                        import_attempts_by_strategy[strategy] = {"success": 0, "failure": 0}
                    
                    if attempt.success:
                        import_attempts_by_strategy[strategy]["success"] += 1
                    else:
                        import_attempts_by_strategy[strategy]["failure"] += 1
                    
                    attempt_detail = {
                        "strategy": strategy,
                        "success": attempt.success,
                        "error_message": attempt.error_message,
                        "duration_ms": attempt.duration_ms,
                        "suggested_fix": attempt.suggested_fix
                    }
                    error_detail["import_attempts"].append(attempt_detail)
            
            report["errors"].append(error_detail)
        
        report["discovery_summary"]["error_types"] = error_type_counts
        
        # Calculate import strategy success rates
        for strategy, stats in import_attempts_by_strategy.items():
            total = stats["success"] + stats["failure"]
            success_rate = (stats["success"] / total * 100) if total > 0 else 0
            report["discovery_summary"]["import_strategy_success_rates"][strategy] = {
                "success_count": stats["success"],
                "failure_count": stats["failure"],
                "success_rate_percent": round(success_rate, 1)
            }
        
        # Generate actionable recommendations based on error patterns
        recommendations = self._generate_actionable_recommendations(error_type_counts, import_attempts_by_strategy)
        report["actionable_recommendations"] = recommendations
        
        return report
    
    def _generate_actionable_recommendations(self, error_types: Dict[str, int], 
                                          import_stats: Dict[str, Dict[str, int]]) -> List[str]:
        """Generate actionable recommendations based on error analysis."""
        recommendations = []
        
        # Recommendations based on error types
        if error_types.get("MODULE_IMPORT_FAILED", 0) > 0:
            recommendations.append(
                "Multiple module import failures detected. Check Python path configuration "
                "and ensure migration files are in the correct directory structure."
            )
        
        if error_types.get("MISSING_VERSION", 0) > 0:
            recommendations.append(
                "Migration classes missing version attributes. Ensure all migration classes "
                "have a 'version' class attribute defined as a string."
            )
        
        if error_types.get("INVALID_INHERITANCE", 0) > 0:
            recommendations.append(
                "Migration classes not inheriting from BaseMigration. Verify imports and "
                "class inheritance: 'class MyMigration(BaseMigration):'."
            )
        
        if error_types.get("MISSING_UP_METHOD", 0) > 0:
            recommendations.append(
                "Migration classes missing up() methods. Implement the required "
                "'def up(self):' method in all migration classes."
            )
        
        # Recommendations based on import strategy performance
        all_strategies_failing = all(
            stats["success"] == 0 for stats in import_stats.values()
        )
        
        if all_strategies_failing and import_stats:
            recommendations.append(
                "All import strategies are failing. This suggests a fundamental issue with "
                "the migration directory structure or Python environment. Check that the "
                "migrations directory exists and contains valid Python files."
            )
        
        # Check for specific strategy patterns
        relative_import_failing = import_stats.get("relative_import", {}).get("success", 0) == 0
        absolute_import_failing = import_stats.get("absolute_import", {}).get("success", 0) == 0
        
        if relative_import_failing and absolute_import_failing:
            recommendations.append(
                "Both relative and absolute imports are failing. Check that __init__.py "
                "files exist in the migration package hierarchy and that the package "
                "structure is correct."
            )
        
        if not recommendations:
            recommendations.append(
                "Enable debug mode for more detailed diagnostic information: "
                "set debug_mode=True when creating the MigrationManager."
            )
        
        return recommendations
    
    def log_diagnostic_report(self) -> None:
        """Log a comprehensive diagnostic report for troubleshooting."""
        report = self.generate_diagnostic_report()
        
        self.logger.info("=== MIGRATION DISCOVERY DIAGNOSTIC REPORT ===")
        self.logger.info(f"Generated at: {report['timestamp']}")
        
        # Environment information
        env = report["environment"]
        self.logger.info(f"Environment:")
        self.logger.info(f"  - Migrations directory: {env['migrations_dir']} (exists: {env['migrations_dir_exists']})")
        self.logger.info(f"  - Python path entries: {env['python_path_length']}")
        self.logger.info(f"  - Import strategies: {', '.join(env['import_strategies'])}")
        self.logger.info(f"  - Debug mode: {env['debug_mode']}")
        self.logger.info(f"  - Current working directory: {env['current_working_dir']}")
        
        # Discovery summary
        summary = report["discovery_summary"]
        self.logger.info(f"Discovery Summary:")
        self.logger.info(f"  - Total errors: {summary['total_errors']}")
        self.logger.info(f"  - Total warnings: {summary['total_warnings']}")
        
        if summary["error_types"]:
            self.logger.info(f"  - Error types:")
            for error_type, count in summary["error_types"].items():
                self.logger.info(f"    * {error_type}: {count}")
        
        if summary["import_strategy_success_rates"]:
            self.logger.info(f"  - Import strategy performance:")
            for strategy, stats in summary["import_strategy_success_rates"].items():
                self.logger.info(
                    f"    * {strategy}: {stats['success_rate_percent']}% "
                    f"({stats['success_count']}/{stats['success_count'] + stats['failure_count']})"
                )
        
        # Actionable recommendations
        if report["actionable_recommendations"]:
            self.logger.info("Actionable Recommendations:")
            for i, recommendation in enumerate(report["actionable_recommendations"], 1):
                self.logger.info(f"  {i}. {recommendation}")
        
        # Detailed errors (only in debug mode)
        if self.debug_mode and report["errors"]:
            self.logger.debug("Detailed Error Information:")
            for error in report["errors"]:
                self.logger.debug(f"  Error: {error['version']} ({error['type']})")
                self.logger.debug(f"    Message: {error['message']}")
                if error.get("suggested_fixes"):
                    self.logger.debug(f"    Suggested fixes:")
                    for fix in error["suggested_fixes"]:
                        self.logger.debug(f"      - {fix}")
        
        self.logger.info("=== END DIAGNOSTIC REPORT ===")
    
    def print_actionable_error_messages(self) -> None:
        """Print user-friendly, actionable error messages for discovered issues."""
        if not self.discovery_errors:
            return
        
        print("\n" + "="*80)
        print("MIGRATION DISCOVERY ISSUES DETECTED")
        print("="*80)
        
        for i, error in enumerate(self.discovery_errors, 1):
            print(f"\n{i}. {error.get_actionable_message()}")
            
            if error.import_attempts and self.debug_mode:
                print("\n   Import attempts:")
                for attempt in error.import_attempts:
                    status = "✅ SUCCESS" if attempt.success else "❌ FAILED"
                    duration = f" ({attempt.duration_ms:.1f}ms)" if attempt.duration_ms else ""
                    print(f"     - {attempt.strategy.value}: {status}{duration}")
                    if not attempt.success and attempt.error_message:
                        print(f"       Error: {attempt.error_message}")
        
        print("\n" + "="*80)
        print("For more detailed diagnostic information, enable debug mode or check the logs.")
        print("="*80 + "\n")
    
    def discover_migrations(self) -> List[Type[BaseMigration]]:
        """
        Discover all migration classes in the migrations directory using enhanced loading.
        
        This method uses multiple fallback strategies and comprehensive error tracking
        to ensure reliable migration discovery across different deployment environments.
        
        Returns:
            List of migration classes sorted by version
        """
        # Reset discovery state for fresh tracking
        self._reset_discovery_state()
        
        migrations = []
        migrations_path = Path(self.migrations_dir)
        
        self.logger.info(f"Discovering migrations in: {migrations_path}")
        
        if not migrations_path.exists():
            self.logger.warning(f"Migrations directory does not exist: {migrations_path}")
            return migrations
        
        # Find all Python files that look like migrations
        migration_files = list(migrations_path.glob("*.py"))
        migration_files = [f for f in migration_files if not f.name.startswith("__")]
        
        self.logger.info(f"Found {len(migration_files)} potential migration files")
        
        for file_path in migration_files:
            try:
                self.logger.debug(f"Processing migration file: {file_path.name}")
                
                # Load the migration module using enhanced loading
                module = self._load_migration_module(file_path)
                
                if module is None:
                    # Error already tracked in _load_migration_module
                    continue
                
                # Extract migration classes from the loaded module
                migration_classes = self._extract_migration_classes_from_module(module, file_path)
                
                if not migration_classes:
                    self.discovery_warnings.append(
                        f"No valid migration classes found in {file_path.name}"
                    )
                    continue
                
                # Add discovered classes to our list
                migrations.extend(migration_classes)
                
                self.logger.debug(
                    f"Successfully discovered {len(migration_classes)} migration(s) "
                    f"from {file_path.name}: {[cls.__name__ for cls in migration_classes]}"
                )
            
            except Exception as e:
                # Handle unexpected errors during discovery
                self._handle_migration_discovery_error(file_path, e)
                continue
        
        # Sort migrations by version
        migrations.sort(key=lambda m: m.version)
        
        # Log discovery summary with enhanced diagnostics
        self.logger.info(f"Migration discovery completed:")
        self.logger.info(f"  - Discovered: {len(migrations)} migrations")
        self.logger.info(f"  - Errors: {len(self.discovery_errors)}")
        self.logger.info(f"  - Warnings: {len(self.discovery_warnings)}")
        
        if migrations:
            migration_versions = [m.version for m in migrations]
            self.logger.info(f"  - Migration versions: {', '.join(migration_versions)}")
        
        # Log errors with actionable messages
        if self.discovery_errors:
            self.logger.error("Discovery errors encountered:")
            for error in self.discovery_errors:
                self.logger.error(f"  - {error.version}: {error.error_message}")
                
                # Log suggested fixes in debug mode
                if self.debug_mode and error.suggested_fixes:
                    self.logger.debug(f"    Suggested fixes for {error.version}:")
                    for fix in error.suggested_fixes:
                        self.logger.debug(f"      * {fix}")
        
        if self.discovery_warnings:
            self.logger.warning("Discovery warnings:")
            for warning in self.discovery_warnings:
                self.logger.warning(f"  - {warning}")
        
        # Generate and log diagnostic report if there are issues
        if (self.discovery_errors or self.discovery_warnings) and self.debug_mode:
            self.log_diagnostic_report()
        
        # Print actionable error messages for user-facing issues
        if self.discovery_errors:
            self.print_actionable_error_messages()
        
        # Log session summary from module loader
        if hasattr(self.module_loader, 'diagnostic_logger'):
            self.module_loader.diagnostic_logger.log_discovery_session_summary()
        
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
        Validate that applied migrations haven't been modified with enhanced error handling.
        
        This method distinguishes between missing files and other validation errors,
        implements graceful handling of migration instances that cannot be created,
        and provides detailed error classification for troubleshooting.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Discover migrations with enhanced error tracking
        all_migrations = self.discover_migrations()
        applied_migrations = self.get_applied_migrations()
        
        # Create a lookup for migration classes by version
        migration_classes = {m.version: m for m in all_migrations}
        
        # Track different types of validation issues
        missing_files = []
        import_failures = []
        instantiation_failures = []
        checksum_mismatches = []
        validation_failures = []
        
        # Process discovery errors first to classify them properly
        from .discovery import ValidationErrorType
        for discovery_error in self.discovery_errors:
            if discovery_error.error_type == ValidationErrorType.MODULE_IMPORT_FAILED.value:
                import_failures.append({
                    'version': discovery_error.version,
                    'error': discovery_error,
                    'applied': discovery_error.version in applied_migrations
                })
            elif discovery_error.error_type in [
                ValidationErrorType.DISCOVERY_ERROR.value, 
                ValidationErrorType.VALIDATION_ERROR.value
            ]:
                validation_failures.append({
                    'version': discovery_error.version,
                    'error': discovery_error,
                    'applied': discovery_error.version in applied_migrations
                })
        
        # Validate each applied migration with enhanced error classification
        for version, applied_migration in applied_migrations.items():
            try:
                # Check if migration class was discovered
                if version not in migration_classes:
                    # Determine if this is a missing file or import failure
                    import_failure = next(
                        (failure for failure in import_failures if failure['version'] == version),
                        None
                    )
                    
                    validation_failure = next(
                        (failure for failure in validation_failures if failure['version'] == version),
                        None
                    )
                    
                    if import_failure:
                        # This is an import failure, not a missing file
                        error_details = import_failure['error']
                        errors.append(
                            f"Applied migration {version} could not be loaded due to import failure: "
                            f"{error_details.error_message}"
                        )
                        
                        # Add detailed import attempt information if available
                        if error_details.import_attempts and self.debug_mode:
                            self.logger.debug(f"Import attempts for {version}:")
                            for attempt in error_details.import_attempts:
                                self.logger.debug(f"  - {attempt.strategy.value}: {attempt.error_message}")
                    
                    elif validation_failure:
                        # This is a validation failure during discovery
                        error_details = validation_failure['error']
                        errors.append(
                            f"Applied migration {version} failed validation during discovery: "
                            f"{error_details.error_message}"
                        )
                    
                    else:
                        # Check if there's a discovery error for a file with similar name
                        # (e.g., version "002" but file is "002_syntax_error.py")
                        similar_error = None
                        for discovery_error in self.discovery_errors:
                            if discovery_error.version.startswith(version) or version in discovery_error.version:
                                similar_error = discovery_error
                                break
                        
                        if similar_error:
                            # Found a related discovery error
                            if similar_error.error_type == ValidationErrorType.MODULE_IMPORT_FAILED.value:
                                errors.append(
                                    f"Applied migration {version} could not be loaded due to import failure "
                                    f"in file {similar_error.file_path}: {similar_error.error_message}"
                                )
                            else:
                                errors.append(
                                    f"Applied migration {version} failed discovery: {similar_error.error_message}"
                                )
                        else:
                            # Check if migration file actually exists on filesystem
                            migration_file_path = Path(self.migrations_dir) / f"{version}.py"
                            if migration_file_path.exists():
                                # File exists but wasn't discovered - this is unusual
                                errors.append(
                                    f"Applied migration {version} file exists but was not discovered "
                                    f"(possible discovery logic issue)"
                                )
                            else:
                                # File is truly missing from filesystem
                                missing_files.append(version)
                                errors.append(
                                    f"Applied migration {version} file not found in migration directory "
                                    f"({migration_file_path})"
                                )
                    
                    continue
                
                # Migration class was discovered, now validate it
                migration_class = migration_classes[version]
                
                # Attempt to create instance for validation
                try:
                    temp_instance = migration_class(self.session)
                    
                    # Validate the instance structure and functionality
                    instance_validation = self.validation_helper.validate_migration_instance(temp_instance)
                    
                    # Add instance validation warnings to our tracking
                    self.discovery_warnings.extend(instance_validation.warnings)
                    
                    # Check if instance validation failed
                    if not instance_validation.is_valid:
                        validation_failures.append({
                            'version': version,
                            'errors': instance_validation.errors,
                            'applied': True
                        })
                        
                        for error in instance_validation.errors:
                            errors.append(
                                f"Applied migration {version} instance validation failed: "
                                f"{error.error_message}"
                            )
                        continue
                    
                    # Attempt checksum validation
                    try:
                        current_checksum = temp_instance.get_checksum()
                        
                        if current_checksum != applied_migration.checksum:
                            checksum_mismatches.append({
                                'version': version,
                                'expected': applied_migration.checksum,
                                'actual': current_checksum
                            })
                            
                            errors.append(
                                f"Applied migration {version} has been modified after application "
                                f"(checksum mismatch: expected {applied_migration.checksum}, "
                                f"got {current_checksum})"
                            )
                    
                    except Exception as checksum_error:
                        # Checksum generation failed - this is a validation issue
                        errors.append(
                            f"Applied migration {version} checksum validation failed: "
                            f"{str(checksum_error)}"
                        )
                        
                        self.logger.error(f"Checksum validation failed for {version}: {str(checksum_error)}")
                        if self.debug_mode:
                            import traceback
                            self.logger.debug(f"Checksum error stack trace: {traceback.format_exc()}")
                
                except Exception as instantiation_error:
                    # Migration instance could not be created
                    instantiation_failures.append({
                        'version': version,
                        'error': str(instantiation_error),
                        'applied': True
                    })
                    
                    errors.append(
                        f"Applied migration {version} cannot be instantiated for validation: "
                        f"{str(instantiation_error)}"
                    )
                    
                    self.logger.error(f"Failed to instantiate migration {version}: {str(instantiation_error)}")
                    if self.debug_mode:
                        import traceback
                        self.logger.debug(f"Instantiation error stack trace: {traceback.format_exc()}")
            
            except Exception as unexpected_error:
                # Completely unexpected error during validation
                errors.append(
                    f"Unexpected error validating applied migration {version}: "
                    f"{str(unexpected_error)}"
                )
                
                self.logger.error(f"Unexpected validation error for {version}: {str(unexpected_error)}")
                if self.debug_mode:
                    import traceback
                    self.logger.debug(f"Unexpected error stack trace: {traceback.format_exc()}")
        
        # Log summary of validation issues by category
        if self.debug_mode or any([missing_files, import_failures, instantiation_failures, 
                                  checksum_mismatches, validation_failures]):
            self.logger.info("Migration integrity validation summary:")
            self.logger.info(f"  - Missing files: {len(missing_files)}")
            self.logger.info(f"  - Import failures: {len([f for f in import_failures if f['applied']])}")
            self.logger.info(f"  - Instantiation failures: {len(instantiation_failures)}")
            self.logger.info(f"  - Checksum mismatches: {len(checksum_mismatches)}")
            self.logger.info(f"  - Validation failures: {len([f for f in validation_failures if f['applied']])}")
        
        # Provide actionable error messages based on error categories
        if missing_files and self.debug_mode:
            self.logger.error("Missing migration files detected. This usually indicates:")
            self.logger.error("  - Migration files were deleted after being applied")
            self.logger.error("  - Migration directory path is incorrect")
            self.logger.error("  - File system permissions prevent access")
        
        if import_failures and self.debug_mode:
            applied_import_failures = [f for f in import_failures if f['applied']]
            if applied_import_failures:
                self.logger.error("Import failures for applied migrations detected. This usually indicates:")
                self.logger.error("  - Python import path issues")
                self.logger.error("  - Missing dependencies in migration files")
                self.logger.error("  - Syntax errors in migration files")
                self.logger.error("  - Environment or deployment context changes")
        
        if instantiation_failures and self.debug_mode:
            self.logger.error("Migration instantiation failures detected. This usually indicates:")
            self.logger.error("  - Constructor errors in migration classes")
            self.logger.error("  - Missing required dependencies")
            self.logger.error("  - Database connection issues")
        
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
        """Get overall migration status information with enhanced error details."""
        all_migrations = self.discover_migrations()
        applied_migrations = self.get_applied_migrations()
        pending_migrations = self.get_pending_migrations()
        validation_errors = self.validate_migration_integrity()
        
        # Include discovery diagnostics
        discovery_errors = [
            {
                'version': error.version,
                'type': error.error_type,
                'message': error.error_message,
                'file_path': error.file_path,
                'import_attempts': len(error.import_attempts) if error.import_attempts else 0
            }
            for error in self.discovery_errors
        ]
        
        return {
            'total_migrations': len(all_migrations),
            'applied_count': len(applied_migrations),
            'pending_count': len(pending_migrations),
            'validation_errors': validation_errors,
            'discovery_errors': discovery_errors,
            'discovery_warnings': self.discovery_warnings.copy(),
            'has_pending': len(pending_migrations) > 0,
            'has_errors': len(validation_errors) > 0 or len(self.discovery_errors) > 0,
            'has_warnings': len(self.discovery_warnings) > 0
        }
