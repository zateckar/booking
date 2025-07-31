"""
Admin API router for frontend components
Provides API endpoints that match frontend expectations with /admin/api prefix
"""
from fastapi import APIRouter

from . import timezone_api, backup_api, email_api

router = APIRouter()

# Mount API endpoints for frontend components
router.include_router(timezone_api.router, prefix="/timezone", tags=["admin-api-timezone"])
router.include_router(backup_api.router, prefix="/backup", tags=["admin-api-backup"])
router.include_router(email_api.router, prefix="/email", tags=["admin-api-email"])