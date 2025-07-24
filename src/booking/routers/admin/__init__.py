from fastapi import APIRouter

from . import oidc_claims, parking_lots, parking_spaces, users, email_settings, timezone_settings, logs, reports, backup_settings, dynamic_reports, styling_settings

router = APIRouter(tags=["admin"])

router.include_router(parking_lots.router)
router.include_router(parking_spaces.router)
router.include_router(users.router)
router.include_router(oidc_claims.router, prefix="/oidc-claims", tags=["admin-oidc-claims"])
router.include_router(email_settings.router)
router.include_router(timezone_settings.router, prefix="/timezone-settings")
router.include_router(logs.router)
router.include_router(reports.router)
router.include_router(backup_settings.router)
router.include_router(styling_settings.router)
router.include_router(dynamic_reports.router, prefix="/dynamic-reports", tags=["admin-dynamic-reports"])
