"""
Admin routes for migration management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, List

from ...database import get_db
from ...models import User
from ...migrations.runner import MigrationRunner
from ...security import get_current_admin_user

router = APIRouter(prefix="/admin/migrations", tags=["admin", "migrations"])


@router.get("/status")
async def get_migration_status(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get current migration status.
    
    Returns information about applied and pending migrations.
    """
    try:
        runner = MigrationRunner(session=db)
        status = runner.get_status()
        
        # Add more detailed information
        manager = runner._get_session() if hasattr(runner, '_get_session') else db
        from ...migrations.manager import MigrationManager
        migration_manager = MigrationManager(db)
        
        applied_migrations = migration_manager.get_applied_migrations()
        pending_migrations = migration_manager.get_pending_migrations()
        
        # Format applied migrations for API response
        applied_list = []
        for version, migration in sorted(applied_migrations.items()):
            applied_list.append({
                'version': migration.version,
                'description': migration.description,
                'applied_at': migration.applied_at.isoformat() if migration.applied_at else None,
                'execution_time_ms': migration.execution_time_ms,
                'status': migration.status,
                'error_message': migration.error_message
            })
        
        # Format pending migrations
        pending_list = []
        for migration_class in pending_migrations:
            temp_instance = migration_class(db)
            pending_list.append({
                'version': migration_class.version,
                'description': migration_class.description,
                'class_name': migration_class.__name__
            })
        
        return {
            'status': 'success',
            'data': {
                **status,
                'applied_migrations': applied_list,
                'pending_migrations': pending_list,
                'database_ready': not status['has_pending'] and not status['has_errors']
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get migration status: {str(e)}"
        )


@router.post("/run")
async def run_migrations(
    request: Request,
    dry_run: bool = False,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Run pending migrations.
    
    Args:
        dry_run: If True, validate migrations but don't apply them
    """
    try:
        runner = MigrationRunner(session=db)
        
        # Check current status first
        status = runner.get_status()
        
        if not status['has_pending']:
            return {
                'status': 'success',
                'message': 'No pending migrations found. Database is up to date.',
                'migrations_applied': 0
            }
        
        # Run migrations
        success = runner.run_migrations(dry_run=dry_run)
        
        if success:
            # Get updated status
            new_status = runner.get_status()
            migrations_applied = status['pending_count']
            
            return {
                'status': 'success',
                'message': f"{'Validated' if dry_run else 'Applied'} {migrations_applied} migration(s) successfully",
                'migrations_applied': migrations_applied,
                'dry_run': dry_run,
                'database_ready': not new_status['has_pending'] and not new_status['has_errors']
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Migration process failed. Check application logs for details."
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run migrations: {str(e)}"
        )


@router.post("/rollback/{version}")
async def rollback_migration(
    request: Request,
    version: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Rollback a specific migration.
    
    Args:
        version: Version of the migration to rollback
    """
    try:
        runner = MigrationRunner(session=db)
        success = runner.rollback_migration(version)
        
        if success:
            return {
                'status': 'success',
                'message': f"Migration {version} rolled back successfully",
                'rolled_back_version': version
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to rollback migration {version}. Check application logs for details."
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rollback migration {version}: {str(e)}"
        )


@router.get("/health")
async def migration_health_check(db: Session = Depends(get_db)) -> Dict:
    """
    Health check endpoint for migrations.
    
    This endpoint can be used by monitoring systems to check
    if the database schema is up to date.
    """
    try:
        runner = MigrationRunner(session=db)
        ready = runner.check_database_ready()
        status = runner.get_status()
        
        return {
            'status': 'healthy' if ready else 'unhealthy',
            'database_ready': ready,
            'total_migrations': status['total_migrations'],
            'applied_count': status['applied_count'],
            'pending_count': status['pending_count'],
            'has_errors': status['has_errors'],
            'validation_errors': status['validation_errors'] if status['has_errors'] else []
        }
    
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'database_ready': False
        }
