"""
Enhanced migration discovery utilities for robust migration loading.

This module provides utilities for discovering and loading migration classes
with multiple fallback strategies and comprehensive error handling.
"""

import os
import sys
import time
import importlib
import importlib.util
import traceback
import logging
from pathlib import Path
from typing import List, Dict, Optional, Type, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .base import BaseMigration


class ImportStrategy(Enum):
    """Available import strategies for loading migration modules."""
    RELATIVE_IMPORT = "relative_import"
    ABSOLUTE_IMPORT = "absolute_import"
    DIRECT_FILE_LOADING = "direct_file_loading"
    SYSPATH_MANIPULATION = "syspath_manipulation"


class ValidationErrorType(Enum):
    """Types of validation errors that can occur during migration discovery."""
    MIGRATION_FILE_NOT_FOUND = "MIGRATION_FILE_NOT_FOUND"
    MIGRATION_IMPORT_FAILED = "MIGRATION_IMPORT_FAILED"
    MIGRATION_CLASS_INVALID = "MIGRATION_CLASS_INVALID"
    MIGRATION_CHECKSUM_MISMATCH = "MIGRATION_CHECKSUM_MISMATCH"
    MIGRATION_INSTANTIATION_FAILED = "MIGRATION_INSTANTIATION_FAILED"
    MODULE_IMPORT_FAILED = "MODULE_IMPORT_FAILED"
    DISCOVERY_ERROR = "DISCOVERY_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INHERITANCE = "INVALID_INHERITANCE"
    MISSING_VERSION = "MISSING_VERSION"
    EMPTY_VERSION = "EMPTY_VERSION"
    INVALID_VERSION_TYPE = "INVALID_VERSION_TYPE"
    MISSING_UP_METHOD = "MISSING_UP_METHOD"
    INVALID_UP_METHOD = "INVALID_UP_METHOD"
    INSTANCE_VALIDATION_ERROR = "INSTANCE_VALIDATION_ERROR"


@dataclass
class ImportAttempt:
    """Record of a single import attempt with detailed diagnostic information."""
    strategy: ImportStrategy
    module_name: str
    success: bool
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    duration_ms: Optional[float] = None
    python_path_used: Optional[List[str]] = None
    file_path_attempted: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class MigrationDiscoveryError:
    """Detailed error information for migration discovery failures with actionable diagnostics."""
    version: str
    error_type: str
    error_message: str
    file_path: Optional[str] = None
    import_attempts: List[ImportAttempt] = field(default_factory=list)
    stack_trace: Optional[str] = None
    suggested_fixes: List[str] = field(default_factory=list)
    diagnostic_info: Dict[str, Any] = field(default_factory=dict)
    severity: str = "ERROR"  # ERROR, WARNING, INFO
    
    def get_actionable_message(self) -> str:
        """Generate an actionable error message with suggested fixes."""
        message = f"Migration {self.version}: {self.error_message}"
        
        if self.suggested_fixes:
            message += "\n\nSuggested fixes:"
            for i, fix in enumerate(self.suggested_fixes, 1):
                message += f"\n  {i}. {fix}"
        
        if self.diagnostic_info:
            message += "\n\nDiagnostic information:"
            for key, value in self.diagnostic_info.items():
                message += f"\n  - {key}: {value}"
        
        return message


@dataclass
class ValidationResult:
    """Comprehensive validation results for migration discovery."""
    is_valid: bool
    errors: List[MigrationDiscoveryError]
    warnings: List[str]
    discovered_migrations: List[Type[BaseMigration]]
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.discovered_migrations is None:
            self.discovered_migrations = []


@dataclass
class MigrationLoadingContext:
    """Environment context for migration loading with diagnostic capabilities."""
    migrations_dir: str
    python_path: Optional[List[str]] = None
    import_strategies: Optional[List[ImportStrategy]] = None
    debug_mode: bool = False
    logger: Optional[logging.Logger] = None
    
    def __post_init__(self):
        if self.python_path is None:
            self.python_path = sys.path.copy()
        if self.import_strategies is None:
            self.import_strategies = list(ImportStrategy)
        if self.logger is None:
            self.logger = logging.getLogger(f"booking.migrations.discovery")
    
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Get diagnostic information about the loading context."""
        return {
            "migrations_dir": self.migrations_dir,
            "migrations_dir_exists": os.path.exists(self.migrations_dir),
            "python_path_length": len(self.python_path),
            "import_strategies": [s.value for s in self.import_strategies],
            "debug_mode": self.debug_mode,
            "current_working_dir": os.getcwd(),
            "python_version": sys.version,
            "sys_modules_count": len(sys.modules)
        }


class MigrationDiagnosticLogger:
    """
    Provides comprehensive diagnostic logging for migration discovery operations.
    
    This class handles detailed logging of import attempts, error classification,
    and generation of actionable error messages with suggested fixes.
    """
    
    def __init__(self, logger: logging.Logger, debug_mode: bool = False):
        self.logger = logger
        self.debug_mode = debug_mode
        self._import_attempt_count = 0
        self._successful_imports = 0
        self._failed_imports = 0
    
    def log_import_attempt_start(self, strategy: ImportStrategy, module_name: str, file_path: Path) -> None:
        """Log the start of an import attempt."""
        self._import_attempt_count += 1
        
        if self.debug_mode:
            self.logger.debug(
                f"Import attempt #{self._import_attempt_count}: "
                f"Trying {strategy.value} for module '{module_name}' from {file_path}"
            )
    
    def log_import_attempt_success(self, attempt: ImportAttempt) -> None:
        """Log a successful import attempt."""
        self._successful_imports += 1
        
        duration_str = f"({attempt.duration_ms:.2f}ms)" if attempt.duration_ms is not None else ""
        self.logger.debug(
            f"✅ Import successful: {attempt.strategy.value} for '{attempt.module_name}' {duration_str}"
        )
        
        if self.debug_mode and attempt.python_path_used:
            self.logger.debug(f"   Python path used: {len(attempt.python_path_used)} entries")
    
    def log_import_attempt_failure(self, attempt: ImportAttempt) -> None:
        """Log a failed import attempt with diagnostic information."""
        self._failed_imports += 1
        
        self.logger.debug(
            f"❌ Import failed: {attempt.strategy.value} for '{attempt.module_name}' - "
            f"{attempt.error_message}"
        )
        
        if self.debug_mode:
            if attempt.duration_ms is not None:
                self.logger.debug(f"   Duration: {attempt.duration_ms:.2f}ms")
            if attempt.file_path_attempted:
                self.logger.debug(f"   File path: {attempt.file_path_attempted}")
            if attempt.suggested_fix:
                self.logger.debug(f"   Suggested fix: {attempt.suggested_fix}")
            if attempt.stack_trace:
                self.logger.debug(f"   Stack trace:\n{attempt.stack_trace}")
    
    def log_module_loading_summary(self, module_name: str, success: bool, attempts: List[ImportAttempt]) -> None:
        """Log a summary of all import attempts for a module."""
        if success:
            successful_strategy = next(a.strategy.value for a in attempts if a.success)
            self.logger.info(
                f"Module '{module_name}' loaded successfully using {successful_strategy} "
                f"(tried {len(attempts)} strategies)"
            )
        else:
            self.logger.warning(
                f"Module '{module_name}' failed to load after {len(attempts)} attempts"
            )
            
            if self.debug_mode:
                self.logger.debug("Failed strategies:")
                for attempt in attempts:
                    self.logger.debug(f"  - {attempt.strategy.value}: {attempt.error_message}")
    
    def log_discovery_session_summary(self) -> None:
        """Log a summary of the entire discovery session."""
        total_attempts = self._import_attempt_count
        success_rate = (self._successful_imports / total_attempts * 100) if total_attempts > 0 else 0
        
        self.logger.info(
            f"Migration discovery session completed: "
            f"{self._successful_imports} successful, {self._failed_imports} failed "
            f"({success_rate:.1f}% success rate)"
        )
    
    def generate_suggested_fixes(self, error_type: str, error_message: str, 
                               file_path: Optional[str] = None) -> List[str]:
        """Generate actionable suggested fixes based on error patterns."""
        fixes = []
        
        error_lower = error_message.lower()
        
        # Import-related fixes
        if "no module named" in error_lower:
            fixes.append("Check that the migration file is in the correct directory")
            fixes.append("Verify that __init__.py files exist in the migration package hierarchy")
            fixes.append("Ensure the Python path includes the migration directory")
            
        if "syntax error" in error_lower or "invalid syntax" in error_lower:
            fixes.append("Check the migration file for Python syntax errors")
            fixes.append("Verify that the file encoding is correct (UTF-8)")
            fixes.append("Run 'python -m py_compile <file>' to check syntax")
            
        if "circular import" in error_lower:
            fixes.append("Remove circular import dependencies in migration files")
            fixes.append("Move shared code to a separate utility module")
            
        if "permission denied" in error_lower:
            fixes.append("Check file system permissions for the migration directory")
            fixes.append("Ensure the application has read access to migration files")
            
        if "file not found" in error_lower or "no such file" in error_lower:
            fixes.append("Verify that the migration file exists in the expected location")
            fixes.append("Check that the file name matches the expected pattern")
            
        # Class-related fixes
        if error_type == ValidationErrorType.MISSING_VERSION.value:
            fixes.append("Add a 'version' class attribute to the migration class")
            fixes.append("Ensure the version is a string (e.g., version = '001')")
            
        if error_type == ValidationErrorType.MISSING_UP_METHOD.value:
            fixes.append("Implement the required 'up(self)' method in the migration class")
            fixes.append("Ensure the migration class inherits from BaseMigration")
            
        if error_type == ValidationErrorType.INVALID_INHERITANCE.value:
            fixes.append("Make sure the migration class inherits from BaseMigration")
            fixes.append("Import BaseMigration: 'from booking.migrations.base import BaseMigration'")
            
        # Environment-related fixes
        if "importlib" in error_lower:
            fixes.append("Check Python version compatibility (requires Python 3.4+)")
            fixes.append("Verify that importlib is available in the current environment")
            
        # Generic fixes if no specific ones were found
        if not fixes:
            fixes.append("Check the migration file for common issues (syntax, imports, class structure)")
            fixes.append("Enable debug mode for more detailed error information")
            fixes.append("Verify that all required dependencies are installed")
        
        return fixes


class ModuleLoader:
    """
    Handles loading migration modules with multiple import strategies and comprehensive logging.
    
    This class implements various fallback strategies to ensure migration
    modules can be loaded across different deployment environments, with
    detailed diagnostic logging and error reporting.
    """
    
    def __init__(self, context: MigrationLoadingContext):
        self.context = context
        self._module_cache: Dict[str, Any] = {}
        self.diagnostic_logger = MigrationDiagnosticLogger(context.logger, context.debug_mode)
    
    def load_module(self, file_path: Path) -> Tuple[Optional[Any], List[ImportAttempt]]:
        """
        Load a migration module using multiple import strategies with comprehensive logging.
        
        Args:
            file_path: Path to the migration file
            
        Returns:
            Tuple of (loaded_module, list_of_import_attempts)
        """
        module_name = file_path.stem
        
        self.context.logger.debug(f"Loading migration module: {module_name} from {file_path}")
        
        # Check cache first
        cache_key = str(file_path)
        if cache_key in self._module_cache:
            self.context.logger.debug(f"Module {module_name} found in cache")
            return self._module_cache[cache_key], []
        
        # Validate file exists before attempting import
        if not file_path.exists():
            self.context.logger.error(f"Migration file does not exist: {file_path}")
            error_attempt = ImportAttempt(
                strategy=ImportStrategy.RELATIVE_IMPORT,  # Placeholder strategy
                module_name=module_name,
                success=False,
                error_message=f"Migration file not found: {file_path}",
                file_path_attempted=str(file_path),
                suggested_fix="Verify that the migration file exists in the expected location"
            )
            return None, [error_attempt]
        
        import_attempts = []
        start_time = time.time()
        
        self.context.logger.info(f"Attempting to load migration module '{module_name}' using {len(self.context.import_strategies)} strategies")
        
        for i, strategy in enumerate(self.context.import_strategies, 1):
            self.diagnostic_logger.log_import_attempt_start(strategy, module_name, file_path)
            
            attempt = self._try_import_strategy(strategy, file_path, module_name)
            import_attempts.append(attempt)
            
            if attempt.success:
                self.diagnostic_logger.log_import_attempt_success(attempt)
                
                # Cache successful module
                module = getattr(attempt, '_module', None)
                if module:
                    self._module_cache[cache_key] = module
                    
                    total_time = (time.time() - start_time) * 1000
                    self.context.logger.info(
                        f"Successfully loaded module '{module_name}' using {strategy.value} "
                        f"(attempt {i}/{len(self.context.import_strategies)}, {total_time:.2f}ms total)"
                    )
                    
                    self.diagnostic_logger.log_module_loading_summary(module_name, True, import_attempts)
                    return module, import_attempts
            else:
                self.diagnostic_logger.log_import_attempt_failure(attempt)
        
        # All strategies failed
        total_time = (time.time() - start_time) * 1000
        self.context.logger.error(
            f"Failed to load module '{module_name}' after trying all {len(self.context.import_strategies)} strategies "
            f"({total_time:.2f}ms total)"
        )
        
        self.diagnostic_logger.log_module_loading_summary(module_name, False, import_attempts)
        return None, import_attempts
    
    def _try_import_strategy(self, strategy: ImportStrategy, file_path: Path, module_name: str) -> ImportAttempt:
        """Try a specific import strategy with detailed timing and error tracking."""
        start_time = time.time()
        
        try:
            if strategy == ImportStrategy.RELATIVE_IMPORT:
                return self._try_relative_import(module_name, file_path, start_time)
            elif strategy == ImportStrategy.ABSOLUTE_IMPORT:
                return self._try_absolute_import(module_name, file_path, start_time)
            elif strategy == ImportStrategy.DIRECT_FILE_LOADING:
                return self._try_direct_file_loading(file_path, module_name, start_time)
            elif strategy == ImportStrategy.SYSPATH_MANIPULATION:
                return self._try_syspath_manipulation(file_path, module_name, start_time)
            else:
                duration_ms = (time.time() - start_time) * 1000
                return ImportAttempt(
                    strategy=strategy,
                    module_name=module_name,
                    success=False,
                    error_message=f"Unknown import strategy: {strategy}",
                    duration_ms=duration_ms,
                    suggested_fix="Use a supported import strategy"
                )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            suggested_fixes = self.diagnostic_logger.generate_suggested_fixes(
                "IMPORT_STRATEGY_ERROR", str(e), str(file_path)
            )
            
            return ImportAttempt(
                strategy=strategy,
                module_name=module_name,
                success=False,
                error_message=str(e),
                stack_trace=traceback.format_exc() if self.context.debug_mode else None,
                duration_ms=duration_ms,
                file_path_attempted=str(file_path),
                suggested_fix=suggested_fixes[0] if suggested_fixes else None
            )
    
    def _try_relative_import(self, module_name: str, file_path: Path, start_time: float) -> ImportAttempt:
        """Try relative import from current package with detailed logging."""
        relative_module_name = f".scripts.{module_name}"
        
        try:
            self.context.logger.debug(f"Attempting relative import: {relative_module_name}")
            
            module = importlib.import_module(relative_module_name, package="booking.migrations")
            duration_ms = (time.time() - start_time) * 1000
            
            attempt = ImportAttempt(
                strategy=ImportStrategy.RELATIVE_IMPORT,
                module_name=relative_module_name,
                success=True,
                duration_ms=duration_ms,
                python_path_used=sys.path.copy(),
                file_path_attempted=str(file_path)
            )
            attempt._module = module  # Store module for retrieval
            return attempt
            
        except ImportError as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            suggested_fixes = []
            if "no module named" in error_msg.lower():
                suggested_fixes.extend([
                    "Ensure the migration file is in the 'scripts' subdirectory",
                    "Check that __init__.py exists in the migrations/scripts directory",
                    "Verify the package structure: booking/migrations/scripts/__init__.py"
                ])
            
            return ImportAttempt(
                strategy=ImportStrategy.RELATIVE_IMPORT,
                module_name=relative_module_name,
                success=False,
                error_message=error_msg,
                stack_trace=traceback.format_exc() if self.context.debug_mode else None,
                duration_ms=duration_ms,
                python_path_used=sys.path.copy(),
                file_path_attempted=str(file_path),
                suggested_fix=suggested_fixes[0] if suggested_fixes else "Check package structure and __init__.py files"
            )
    
    def _try_absolute_import(self, module_name: str, file_path: Path, start_time: float) -> ImportAttempt:
        """Try absolute import with full module path and detailed diagnostics."""
        full_module_name = f"booking.migrations.scripts.{module_name}"
        
        try:
            self.context.logger.debug(f"Attempting absolute import: {full_module_name}")
            
            module = importlib.import_module(full_module_name)
            duration_ms = (time.time() - start_time) * 1000
            
            attempt = ImportAttempt(
                strategy=ImportStrategy.ABSOLUTE_IMPORT,
                module_name=full_module_name,
                success=True,
                duration_ms=duration_ms,
                python_path_used=sys.path.copy(),
                file_path_attempted=str(file_path)
            )
            attempt._module = module
            return attempt
            
        except ImportError as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            suggested_fixes = []
            if "no module named" in error_msg.lower():
                suggested_fixes.extend([
                    "Verify the full package path exists: booking/migrations/scripts/",
                    "Check that all __init__.py files are present in the package hierarchy",
                    "Ensure the migration file is properly named and located"
                ])
            
            return ImportAttempt(
                strategy=ImportStrategy.ABSOLUTE_IMPORT,
                module_name=full_module_name,
                success=False,
                error_message=error_msg,
                stack_trace=traceback.format_exc() if self.context.debug_mode else None,
                duration_ms=duration_ms,
                python_path_used=sys.path.copy(),
                file_path_attempted=str(file_path),
                suggested_fix=suggested_fixes[0] if suggested_fixes else "Check absolute package path and __init__.py files"
            )
    
    def _try_direct_file_loading(self, file_path: Path, module_name: str, start_time: float) -> ImportAttempt:
        """Try direct file loading using importlib.util with comprehensive diagnostics."""
        try:
            self.context.logger.debug(f"Attempting direct file loading: {file_path}")
            
            # Check file accessibility
            if not os.access(file_path, os.R_OK):
                duration_ms = (time.time() - start_time) * 1000
                return ImportAttempt(
                    strategy=ImportStrategy.DIRECT_FILE_LOADING,
                    module_name=module_name,
                    success=False,
                    error_message=f"File is not readable: {file_path}",
                    duration_ms=duration_ms,
                    file_path_attempted=str(file_path),
                    suggested_fix="Check file permissions and ensure the file is readable"
                )
            
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                duration_ms = (time.time() - start_time) * 1000
                return ImportAttempt(
                    strategy=ImportStrategy.DIRECT_FILE_LOADING,
                    module_name=module_name,
                    success=False,
                    error_message="Could not create module spec from file",
                    duration_ms=duration_ms,
                    file_path_attempted=str(file_path),
                    suggested_fix="Verify the file is a valid Python module with correct syntax"
                )
            
            module = importlib.util.module_from_spec(spec)
            
            # Add to sys.modules to support relative imports
            full_module_name = f"booking.migrations.scripts.{module_name}"
            original_module = sys.modules.get(full_module_name)
            sys.modules[full_module_name] = module
            
            try:
                spec.loader.exec_module(module)
                duration_ms = (time.time() - start_time) * 1000
                
                attempt = ImportAttempt(
                    strategy=ImportStrategy.DIRECT_FILE_LOADING,
                    module_name=module_name,
                    success=True,
                    duration_ms=duration_ms,
                    file_path_attempted=str(file_path)
                )
                attempt._module = module
                return attempt
                
            except Exception as exec_error:
                # Restore original module if execution failed
                if original_module is not None:
                    sys.modules[full_module_name] = original_module
                elif full_module_name in sys.modules:
                    del sys.modules[full_module_name]
                raise exec_error
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            suggested_fixes = []
            if "syntax error" in error_msg.lower():
                suggested_fixes.extend([
                    "Check the migration file for Python syntax errors",
                    "Run 'python -m py_compile <file>' to validate syntax",
                    "Ensure proper indentation and valid Python code"
                ])
            elif "permission" in error_msg.lower():
                suggested_fixes.append("Check file system permissions for the migration file")
            elif "encoding" in error_msg.lower():
                suggested_fixes.append("Ensure the file is saved with UTF-8 encoding")
            
            return ImportAttempt(
                strategy=ImportStrategy.DIRECT_FILE_LOADING,
                module_name=module_name,
                success=False,
                error_message=error_msg,
                stack_trace=traceback.format_exc() if self.context.debug_mode else None,
                duration_ms=duration_ms,
                file_path_attempted=str(file_path),
                suggested_fix=suggested_fixes[0] if suggested_fixes else "Check file syntax and permissions"
            )
    
    def _try_syspath_manipulation(self, file_path: Path, module_name: str, start_time: float) -> ImportAttempt:
        """Try import with sys.path manipulation and detailed path tracking."""
        migrations_dir = str(file_path.parent)
        original_path = sys.path.copy()
        
        try:
            self.context.logger.debug(f"Attempting sys.path manipulation: adding {migrations_dir}")
            
            # Add the migrations directory to sys.path temporarily
            path_was_modified = False
            if migrations_dir not in sys.path:
                sys.path.insert(0, migrations_dir)
                path_was_modified = True
                self.context.logger.debug(f"Added {migrations_dir} to sys.path at position 0")
            
            try:
                module = importlib.import_module(module_name)
                duration_ms = (time.time() - start_time) * 1000
                
                attempt = ImportAttempt(
                    strategy=ImportStrategy.SYSPATH_MANIPULATION,
                    module_name=module_name,
                    success=True,
                    duration_ms=duration_ms,
                    python_path_used=sys.path.copy(),
                    file_path_attempted=str(file_path)
                )
                attempt._module = module
                return attempt
                
            finally:
                # Restore original sys.path
                if path_was_modified:
                    sys.path[:] = original_path
                    self.context.logger.debug("Restored original sys.path")
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            suggested_fixes = []
            if "no module named" in error_msg.lower():
                suggested_fixes.extend([
                    "Ensure the migration file is in the expected directory",
                    "Check that the file name matches the module name exactly",
                    "Verify there are no naming conflicts with existing modules"
                ])
            elif "circular import" in error_msg.lower():
                suggested_fixes.append("Remove circular import dependencies")
            
            return ImportAttempt(
                strategy=ImportStrategy.SYSPATH_MANIPULATION,
                module_name=module_name,
                success=False,
                error_message=error_msg,
                stack_trace=traceback.format_exc() if self.context.debug_mode else None,
                duration_ms=duration_ms,
                python_path_used=original_path,
                file_path_attempted=str(file_path),
                suggested_fix=suggested_fixes[0] if suggested_fixes else "Check module name and directory structure"
            )


class ClassExtractor:
    """
    Safely extracts migration classes from loaded modules with comprehensive logging.
    
    This class handles the extraction of migration classes from modules
    with proper validation, error handling, and detailed diagnostic information.
    """
    
    def __init__(self, debug_mode: bool = False, logger: Optional[logging.Logger] = None):
        self.debug_mode = debug_mode
        self.logger = logger or logging.getLogger("booking.migrations.discovery.extractor")
    
    def extract_migration_classes(self, module: Any, file_path: Path) -> Tuple[List[Type[BaseMigration]], List[str]]:
        """
        Extract migration classes from a loaded module with comprehensive logging.
        
        Args:
            module: The loaded module
            file_path: Path to the migration file (for error reporting)
            
        Returns:
            Tuple of (migration_classes, warnings)
        """
        migration_classes = []
        warnings = []
        
        module_name = getattr(module, '__name__', str(module))
        self.logger.debug(f"Extracting migration classes from module: {module_name}")
        
        try:
            module_attributes = dir(module)
            self.logger.debug(f"Module has {len(module_attributes)} attributes: {module_attributes}")
            
            potential_classes = []
            
            # Look for migration classes in the module
            for attr_name in module_attributes:
                try:
                    attr = getattr(module, attr_name)
                    
                    # Check if it's a class
                    if isinstance(attr, type):
                        self.logger.debug(f"Found class: {attr_name}")
                        
                        # Check if it's a migration class
                        if issubclass(attr, BaseMigration) and attr != BaseMigration:
                            potential_classes.append((attr_name, attr))
                            self.logger.debug(f"Class {attr_name} is a migration class")
                            
                            # Validate the migration class
                            validation_warnings = self._validate_migration_class(attr, file_path)
                            warnings.extend(validation_warnings)
                            
                            # Only add if it has a version (valid migration)
                            if hasattr(attr, 'version') and attr.version:
                                migration_classes.append(attr)
                                self.logger.info(f"Successfully extracted migration class: {attr.__name__} (version: {attr.version})")
                            else:
                                warning_msg = (
                                    f"Migration class {attr.__name__} in {file_path.name} "
                                    f"has no version attribute or empty version"
                                )
                                warnings.append(warning_msg)
                                self.logger.warning(warning_msg)
                        else:
                            self.logger.debug(f"Class {attr_name} is not a migration class")
                
                except Exception as e:
                    error_msg = f"Error examining attribute {attr_name} in {file_path.name}: {str(e)}"
                    warnings.append(error_msg)
                    self.logger.warning(error_msg)
                    
                    if self.debug_mode:
                        stack_trace = traceback.format_exc()
                        warnings.append(f"Stack trace: {stack_trace}")
                        self.logger.debug(f"Stack trace for {attr_name}: {stack_trace}")
            
            self.logger.info(
                f"Class extraction completed for {file_path.name}: "
                f"found {len(potential_classes)} potential classes, "
                f"{len(migration_classes)} valid migration classes"
            )
            
            if potential_classes and not migration_classes:
                self.logger.warning(
                    f"Found potential migration classes but none were valid: "
                    f"{[name for name, _ in potential_classes]}"
                )
        
        except Exception as e:
            error_msg = f"Error extracting classes from {file_path.name}: {str(e)}"
            warnings.append(error_msg)
            self.logger.error(error_msg)
            
            if self.debug_mode:
                stack_trace = traceback.format_exc()
                warnings.append(f"Stack trace: {stack_trace}")
                self.logger.debug(f"Stack trace: {stack_trace}")
        
        return migration_classes, warnings
    
    def _validate_migration_class(self, migration_class: Type[BaseMigration], file_path: Path) -> List[str]:
        """
        Validate a migration class structure.
        
        Args:
            migration_class: The migration class to validate
            file_path: Path to the migration file
            
        Returns:
            List of validation warnings
        """
        warnings = []
        
        # Check required attributes
        if not hasattr(migration_class, 'version'):
            warnings.append(f"Migration {migration_class.__name__} missing version attribute")
        elif not migration_class.version:
            warnings.append(f"Migration {migration_class.__name__} has empty version")
        
        if not hasattr(migration_class, 'description'):
            warnings.append(f"Migration {migration_class.__name__} missing description attribute")
        elif not migration_class.description:
            warnings.append(f"Migration {migration_class.__name__} has empty description")
        
        # Check required methods
        if not hasattr(migration_class, 'up'):
            warnings.append(f"Migration {migration_class.__name__} missing up() method")
        elif not callable(getattr(migration_class, 'up')):
            warnings.append(f"Migration {migration_class.__name__} up() is not callable")
        
        # Check if down() method exists (optional but recommended)
        if hasattr(migration_class, 'down'):
            if not callable(getattr(migration_class, 'down')):
                warnings.append(f"Migration {migration_class.__name__} down() is not callable")
        
        return warnings


class ValidationHelper:
    """
    Validates migration class structure and provides detailed diagnostics with comprehensive logging.
    
    This class provides comprehensive validation of migration classes,
    generates actionable error messages, and logs detailed diagnostic information.
    """
    
    def __init__(self, debug_mode: bool = False, logger: Optional[logging.Logger] = None):
        self.debug_mode = debug_mode
        self.logger = logger or logging.getLogger("booking.migrations.discovery.validator")
        self.diagnostic_logger = MigrationDiagnosticLogger(self.logger, debug_mode)
    
    def validate_migration_structure(self, migration_class: Type[BaseMigration]) -> ValidationResult:
        """
        Validate the structure of a migration class with comprehensive logging and diagnostics.
        
        Args:
            migration_class: The migration class to validate
            
        Returns:
            ValidationResult with detailed validation information
        """
        errors = []
        warnings = []
        is_valid = True
        
        class_name = migration_class.__name__
        version = getattr(migration_class, 'version', 'unknown')
        
        self.logger.debug(f"Validating migration class structure: {class_name} (version: {version})")
        
        try:
            # Validate class inheritance
            if not issubclass(migration_class, BaseMigration):
                error = MigrationDiscoveryError(
                    version=version,
                    error_type=ValidationErrorType.INVALID_INHERITANCE.value,
                    error_message=f"Class {class_name} does not inherit from BaseMigration",
                    suggested_fixes=self.diagnostic_logger.generate_suggested_fixes(
                        ValidationErrorType.INVALID_INHERITANCE.value,
                        f"Class {class_name} does not inherit from BaseMigration"
                    ),
                    diagnostic_info={
                        "class_name": class_name,
                        "base_classes": [base.__name__ for base in migration_class.__bases__],
                        "mro": [cls.__name__ for cls in migration_class.__mro__]
                    }
                )
                errors.append(error)
                is_valid = False
                self.logger.error(f"❌ {class_name}: Invalid inheritance")
            else:
                self.logger.debug(f"✅ {class_name}: Valid inheritance from BaseMigration")
            
            # Validate version attribute
            if not hasattr(migration_class, 'version'):
                error = MigrationDiscoveryError(
                    version='unknown',
                    error_type=ValidationErrorType.MISSING_VERSION.value,
                    error_message=f"Migration class {class_name} missing version attribute",
                    suggested_fixes=self.diagnostic_logger.generate_suggested_fixes(
                        ValidationErrorType.MISSING_VERSION.value,
                        f"Migration class {class_name} missing version attribute"
                    ),
                    diagnostic_info={
                        "class_name": class_name,
                        "available_attributes": [attr for attr in dir(migration_class) if not attr.startswith('_')]
                    }
                )
                errors.append(error)
                is_valid = False
                self.logger.error(f"❌ {class_name}: Missing version attribute")
            elif not getattr(migration_class, 'version', None):
                error = MigrationDiscoveryError(
                    version='',
                    error_type=ValidationErrorType.EMPTY_VERSION.value,
                    error_message=f"Migration class {class_name} has empty version",
                    suggested_fixes=self.diagnostic_logger.generate_suggested_fixes(
                        ValidationErrorType.EMPTY_VERSION.value,
                        f"Migration class {class_name} has empty version"
                    ),
                    diagnostic_info={
                        "class_name": class_name,
                        "version_value": repr(getattr(migration_class, 'version', None)),
                        "version_type": type(getattr(migration_class, 'version', None)).__name__
                    }
                )
                errors.append(error)
                is_valid = False
                self.logger.error(f"❌ {class_name}: Empty version attribute")
            elif not isinstance(migration_class.version, str):
                error = MigrationDiscoveryError(
                    version=str(migration_class.version),
                    error_type=ValidationErrorType.INVALID_VERSION_TYPE.value,
                    error_message=f"Migration class {class_name} version must be a string",
                    suggested_fixes=[
                        f"Change version to a string: version = '{migration_class.version}'",
                        "Ensure version is defined as a string literal"
                    ],
                    diagnostic_info={
                        "class_name": class_name,
                        "version_value": repr(migration_class.version),
                        "version_type": type(migration_class.version).__name__,
                        "expected_type": "str"
                    }
                )
                errors.append(error)
                is_valid = False
                self.logger.error(f"❌ {class_name}: Invalid version type ({type(migration_class.version).__name__})")
            else:
                self.logger.debug(f"✅ {class_name}: Valid version attribute ({migration_class.version})")
            
            # Validate description attribute
            if not hasattr(migration_class, 'description'):
                warning_msg = f"Migration {class_name} missing description attribute"
                warnings.append(warning_msg)
                self.logger.warning(f"⚠️  {class_name}: Missing description attribute")
            elif not migration_class.description:
                warning_msg = f"Migration {class_name} has empty description"
                warnings.append(warning_msg)
                self.logger.warning(f"⚠️  {class_name}: Empty description")
            else:
                self.logger.debug(f"✅ {class_name}: Has description")
            
            # Validate up() method
            if not hasattr(migration_class, 'up'):
                error = MigrationDiscoveryError(
                    version=version,
                    error_type=ValidationErrorType.MISSING_UP_METHOD.value,
                    error_message=f"Migration class {class_name} missing up() method",
                    suggested_fixes=self.diagnostic_logger.generate_suggested_fixes(
                        ValidationErrorType.MISSING_UP_METHOD.value,
                        f"Migration class {class_name} missing up() method"
                    ),
                    diagnostic_info={
                        "class_name": class_name,
                        "available_methods": [method for method in dir(migration_class) 
                                            if callable(getattr(migration_class, method)) and not method.startswith('_')]
                    }
                )
                errors.append(error)
                is_valid = False
                self.logger.error(f"❌ {class_name}: Missing up() method")
            elif not callable(getattr(migration_class, 'up', None)):
                error = MigrationDiscoveryError(
                    version=version,
                    error_type=ValidationErrorType.INVALID_UP_METHOD.value,
                    error_message=f"Migration class {class_name} up() is not callable",
                    suggested_fixes=[
                        "Ensure up() is defined as a method: def up(self):",
                        "Check that up() is not overridden by a non-callable attribute"
                    ],
                    diagnostic_info={
                        "class_name": class_name,
                        "up_attribute_type": type(getattr(migration_class, 'up', None)).__name__,
                        "up_attribute_value": repr(getattr(migration_class, 'up', None))
                    }
                )
                errors.append(error)
                is_valid = False
                self.logger.error(f"❌ {class_name}: up() is not callable")
            else:
                self.logger.debug(f"✅ {class_name}: Has callable up() method")
            
            # Test instantiation (optional validation) - only if class is not abstract
            try:
                import inspect
                if not inspect.isabstract(migration_class):
                    self.logger.debug(f"Testing instantiation for {class_name}")
                    
                    # Try to create a temporary instance to check for constructor issues
                    # We'll use None as session for this test - migration should handle this gracefully
                    temp_instance = migration_class(None)
                    
                    if not hasattr(temp_instance, 'get_checksum'):
                        warning_msg = f"Migration {class_name} may not properly inherit checksum functionality"
                        warnings.append(warning_msg)
                        self.logger.warning(f"⚠️  {class_name}: Missing checksum functionality")
                    else:
                        self.logger.debug(f"✅ {class_name}: Instantiation successful")
                else:
                    # If class is abstract, it means required methods are missing
                    warning_msg = f"Migration {class_name} is abstract - missing required method implementations"
                    warnings.append(warning_msg)
                    self.logger.warning(f"⚠️  {class_name}: Class is abstract")
                    
            except Exception as e:
                warning_msg = f"Migration {class_name} constructor validation failed: {str(e)}"
                warnings.append(warning_msg)
                self.logger.warning(f"⚠️  {class_name}: Constructor validation failed - {str(e)}")
                
                if self.debug_mode:
                    stack_trace = traceback.format_exc()
                    warnings.append(f"Constructor stack trace: {stack_trace}")
                    self.logger.debug(f"Constructor stack trace for {class_name}:\n{stack_trace}")
        
        except Exception as e:
            error = MigrationDiscoveryError(
                version=version,
                error_type=ValidationErrorType.VALIDATION_ERROR.value,
                error_message=f"Unexpected error validating {class_name}: {str(e)}",
                stack_trace=traceback.format_exc() if self.debug_mode else None,
                suggested_fixes=[
                    "Check the migration class for syntax errors or import issues",
                    "Enable debug mode for more detailed error information",
                    "Verify that all required dependencies are available"
                ],
                diagnostic_info={
                    "class_name": class_name,
                    "error_type": type(e).__name__,
                    "validation_step": "structure_validation"
                }
            )
            errors.append(error)
            is_valid = False
            self.logger.error(f"❌ {class_name}: Unexpected validation error - {str(e)}")
            
            if self.debug_mode:
                self.logger.debug(f"Validation error stack trace for {class_name}:\n{traceback.format_exc()}")
        
        # Log validation summary
        if is_valid:
            self.logger.info(f"✅ Migration class {class_name} passed structure validation")
        else:
            self.logger.error(f"❌ Migration class {class_name} failed structure validation ({len(errors)} errors)")
        
        if warnings:
            self.logger.info(f"⚠️  Migration class {class_name} has {len(warnings)} warnings")
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            discovered_migrations=[migration_class] if is_valid else []
        )
    
    def validate_migration_instance(self, migration_instance: BaseMigration) -> ValidationResult:
        """
        Validate a migration instance.
        
        Args:
            migration_instance: The migration instance to validate
            
        Returns:
            ValidationResult with detailed validation information
        """
        errors = []
        warnings = []
        is_valid = True
        
        try:
            # Test checksum generation
            try:
                checksum = migration_instance.get_checksum()
                if not checksum or not isinstance(checksum, str):
                    warnings.append(f"Migration {migration_instance.__class__.__name__} checksum generation returned invalid result")
            except Exception as e:
                warnings.append(f"Migration {migration_instance.__class__.__name__} checksum generation failed: {str(e)}")
            
            # Test validation method
            try:
                validation_result = migration_instance.validate()
                if not isinstance(validation_result, bool):
                    warnings.append(f"Migration {migration_instance.__class__.__name__} validate() should return boolean")
            except Exception as e:
                warnings.append(f"Migration {migration_instance.__class__.__name__} validate() method failed: {str(e)}")
            
            # Test info generation
            try:
                info = migration_instance.get_info()
                if not isinstance(info, dict):
                    warnings.append(f"Migration {migration_instance.__class__.__name__} get_info() should return dict")
                else:
                    required_keys = ['version', 'description', 'checksum', 'class_name']
                    missing_keys = [key for key in required_keys if key not in info]
                    if missing_keys:
                        warnings.append(f"Migration {migration_instance.__class__.__name__} get_info() missing keys: {missing_keys}")
            except Exception as e:
                warnings.append(f"Migration {migration_instance.__class__.__name__} get_info() method failed: {str(e)}")
        
        except Exception as e:
            errors.append(MigrationDiscoveryError(
                version=getattr(migration_instance, 'version', 'unknown'),
                error_type=ValidationErrorType.INSTANCE_VALIDATION_ERROR.value,
                error_message=f"Unexpected error validating instance: {str(e)}",
                stack_trace=traceback.format_exc() if self.debug_mode else None
            ))
            is_valid = False
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            discovered_migrations=[migration_instance.__class__] if is_valid else []
        )