# Database Migration System

This document describes the comprehensive database migration system implemented for the booking application to handle schema changes safely in production environments.

## Overview

The migration system provides:
- ✅ **Version tracking** - Every migration is tracked with version, checksum, and execution status
- ✅ **Automatic execution** - Migrations run automatically on application startup
- ✅ **Rollback capabilities** - Safe rollback of applied migrations
- ✅ **Validation** - Integrity checks and dry-run mode
- ✅ **CLI tools** - Command-line interface for deployment automation
- ✅ **Web interface** - Admin panel for migration management
- ✅ **Production safety** - Multiple safety mechanisms to prevent data loss

## Architecture

### Core Components

```
src/booking/migrations/
├── __init__.py              # Main migration module
├── base.py                  # BaseMigration class
├── manager.py               # MigrationManager for discovery & execution
├── runner.py                # MigrationRunner high-level interface
└── scripts/                 # Migration files
    ├── __init__.py
    ├── 001_initial_schema.py
    ├── 002_user_cascade_delete.py
    └── ...
```

### Database Tracking

The `schema_migrations` table tracks all applied migrations:
- **version**: Migration version (e.g., "001", "002")
- **description**: Human-readable description
- **checksum**: MD5 hash to detect file changes
- **applied_at**: Timestamp of application
- **execution_time_ms**: Performance tracking
- **status**: "applied", "failed", or "rolled_back"
- **error_message**: Error details for failed migrations

## Creating Migrations

### 1. Migration File Structure

Create new migration files in `src/booking/migrations/scripts/`:

```python
# src/booking/migrations/scripts/003_add_new_feature.py
"""
Add new feature to the application.

This migration adds a new table and modifies existing tables
to support the new feature functionality.
"""

from sqlalchemy import text
from ..base import BaseMigration


class AddNewFeatureMigration(BaseMigration):
    """Add new feature support."""
    
    version = "003"
    description = "Add new feature tables and columns"
    
    def up(self) -> None:
        """Apply the migration."""
        # Create new table
        self.session.execute(text("""
            CREATE TABLE new_feature (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Add column to existing table
        self.session.execute(text("""
            ALTER TABLE users ADD COLUMN feature_enabled BOOLEAN DEFAULT 0
        """))
        
        self.session.commit()
        print("✅ New feature tables created successfully")
    
    def down(self) -> None:
        """Rollback the migration."""
        # Remove added column (SQLite limitation - requires table recreation)
        self.session.execute(text("DROP TABLE IF EXISTS new_feature"))
        
        # For SQLite, removing columns requires table recreation
        # This is a simplified example - real rollback might be more complex
        print("⚠️  Column removal requires manual intervention in SQLite")
        
        self.session.commit()
    
    def validate(self) -> bool:
        """Validate migration prerequisites."""
        try:
            # Check that users table exists
            self.session.execute(text("SELECT COUNT(*) FROM users LIMIT 1"))
            return True
        except Exception:
            return False
```

### 2. Naming Convention

- Use sequential numbering: `001`, `002`, `003`, etc.
- Include descriptive name: `001_initial_schema.py`
- Class name should end with `Migration`

### 3. Best Practices

- **Atomic operations**: Each migration should be a single logical change
- **Backward compatibility**: Consider data preservation during schema changes
- **Validation**: Implement `validate()` method to check prerequisites
- **Error handling**: Use try/catch blocks for complex operations
- **Documentation**: Include clear description and comments
- **Testing**: Test rollback functionality when possible

## Running Migrations

### 1. Automatic Execution

Migrations run automatically when the application starts:

```python
# In src/booking/database.py
def create_db_and_tables():
    """Create database tables, run migrations, and create initial admin user"""
    # First, create base tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    # Run any pending migrations
    from .migrations.runner import run_migrations
    try:
        print("🔍 Checking for pending migrations...")
        if not run_migrations():
            print("⚠️  Some migrations failed. Please check the logs.")
    except Exception as e:
        print(f"⚠️  Migration check failed: {e}")
    
    # Create initial admin user after migrations
    create_initial_admin_user()
```

### 2. CLI Tool

Use the `migrate.py` script for manual migration management:

```bash
# Run all pending migrations
python migrate.py run

# Dry-run (validation only)
python migrate.py run --dry-run

# Run migrations up to specific version
python migrate.py run --target 002

# Check migration status
python migrate.py status

# Check if database is ready
python migrate.py check

# Rollback specific migration
python migrate.py rollback --version 002
```

### 3. Web Interface

Access migration management through the admin panel:

- **GET** `/admin/migrations/status` - View migration status
- **POST** `/admin/migrations/run` - Run pending migrations
- **POST** `/admin/migrations/run?dry_run=true` - Validate migrations
- **POST** `/admin/migrations/rollback/{version}` - Rollback migration
- **GET** `/admin/migrations/health` - Health check endpoint

## Production Deployment

### 1. Pre-deployment Validation

```bash
# Validate migrations before deployment
python migrate.py run --dry-run

# Check current status
python migrate.py status
```

### 2. Deployment Process

```bash
#!/bin/bash
# deployment script

echo "🚀 Starting deployment..."

# 1. Backup database (recommended)
cp app/data/booking.db app/data/booking.db.backup.$(date +%Y%m%d_%H%M%S)

# 2. Run migrations
echo "📝 Running database migrations..."
python migrate.py run

if [ $? -ne 0 ]; then
    echo "❌ Migration failed! Rolling back..."
    cp app/data/booking.db.backup.* app/data/booking.db
    exit 1
fi

# 3. Start application
echo "✅ Migrations completed successfully"
echo "🚀 Starting application..."
# ... start application
```

### 3. Health Checks

Monitor migration status:

```bash
# Check if database is ready
python migrate.py check
echo $?  # 0 = ready, 1 = error, 2 = not ready

# HTTP health check
curl http://localhost:8000/admin/migrations/health
```

## Rollback Procedures

### 1. Automatic Rollback

```bash
# Rollback specific migration
python migrate.py rollback --version 003
```

### 2. Manual Rollback

For complex rollbacks or when automatic rollback fails:

1. **Stop the application**
2. **Restore database backup**
3. **Run migrations up to desired state**

```bash
# Restore backup
cp app/data/booking.db.backup.20250124_120000 app/data/booking.db

# Run migrations up to specific version
python migrate.py run --target 002
```

## Monitoring and Troubleshooting

### 1. Status Monitoring

```bash
# Detailed status report
python migrate.py status

# JSON status for monitoring systems
curl http://localhost:8000/admin/migrations/health
```

### 2. Common Issues

**Migration Integrity Errors:**
- Migration file was modified after application
- Solution: Revert file changes or create new migration

**Failed Migrations:**
- Check application logs for error details
- Verify database permissions and connectivity
- Ensure prerequisite data exists

**Rollback Failures:**
- Some migrations may not support rollback
- Use database backup for recovery
- Manual intervention may be required

### 3. Logging

Migration operations are logged with detailed information:
- Migration execution times
- Success/failure status
- Error messages and stack traces
- Validation results

## Security Considerations

1. **Admin Access**: Migration endpoints require admin privileges
2. **Backup Strategy**: Always backup before migrations in production
3. **Validation**: Use dry-run mode to validate before applying
4. **Monitoring**: Set up alerts for migration failures
5. **Access Control**: Limit migration execution to authorized personnel

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Deploy with Migrations

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Validate Migrations
        run: python migrate.py run --dry-run
        
      - name: Deploy Application
        run: |
          # Deploy application code
          # Run migrations
          python migrate.py run
          
      - name: Health Check
        run: python migrate.py check
```

## Migration Examples

See the existing migration files for examples:
- `001_initial_schema.py` - Initial schema validation
- `002_user_cascade_delete.py` - Complex table modification with rollback

## Support

For migration-related issues:
1. Check the application logs
2. Use `python migrate.py status` for detailed information
3. Review this documentation for best practices
4. Contact the development team for complex migration scenarios
