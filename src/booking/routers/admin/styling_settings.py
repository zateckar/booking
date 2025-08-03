import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import StylingSettings
from ...schemas import StylingSettings as StylingSettingsSchema
from ...schemas import StylingSettingsUpdate
from ...security import get_current_admin_user
from ...logging_config import get_logger

router = APIRouter(prefix="/styling-settings", tags=["admin", "styling"])
logger = get_logger("styling_admin")

# Allowed file extensions for logo uploads
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.svg', '.gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
UPLOAD_DIR = Path("static/uploads/logos")

# Ensure upload directory exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_styling_settings(db: Session) -> StylingSettings:
    """Get or create styling settings"""
    settings = db.query(StylingSettings).first()
    if not settings:
        settings = StylingSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/", response_model=StylingSettingsSchema)
def get_current_styling_settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Get current styling settings"""
    logger.info("Fetching styling settings")
    return get_styling_settings(db)


@router.put("/", response_model=StylingSettingsSchema)
def update_styling_settings(
    request: Request,
    settings_update: StylingSettingsUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Update styling settings"""
    logger.info("Updating styling settings")
    
    settings = get_styling_settings(db)
    
    # Update only provided fields
    update_data = settings_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    
    logger.info("Styling settings updated successfully")
    return settings


@router.post("/upload-logo")
def upload_logo(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Upload a logo file"""
    logger.info(f"Uploading logo file: {file.filename}")
    
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    file_content = file.file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Update database with relative path for web serving
        settings = get_styling_settings(db)
        
        # Remove old logo file if exists
        if settings.logo_path:
            old_file_path = Path("static") / settings.logo_path.lstrip("/static/")
            if old_file_path.exists():
                old_file_path.unlink()
        
        # Store relative path from static directory
        relative_path = f"/static/uploads/logos/{unique_filename}"
        settings.logo_path = relative_path
        
        db.commit()
        
        logger.info(f"Logo uploaded successfully: {relative_path}")
        return {"message": "Logo uploaded successfully", "logo_path": relative_path}
        
    except Exception as e:
        # Clean up file if database update fails
        if file_path.exists():
            file_path.unlink()
        logger.error(f"Failed to upload logo: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload logo")


@router.delete("/logo")
def delete_logo(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Delete current logo"""
    logger.info("Deleting logo")
    
    settings = get_styling_settings(db)
    
    if not settings.logo_path:
        raise HTTPException(status_code=404, detail="No logo to delete")
    
    # Remove file
    file_path = Path("static") / settings.logo_path.lstrip("/static/")
    if file_path.exists():
        file_path.unlink()
    
    # Update database
    settings.logo_path = None
    db.commit()
    
    logger.info("Logo deleted successfully")
    return {"message": "Logo deleted successfully"}


@router.get("/dynamic-styles.css")
def get_dynamic_styles(
    db: Session = Depends(get_db)
):
    """Generate dynamic CSS based on current styling settings"""
    try:
        settings = get_styling_settings(db)
        
        if not settings.enabled:
            # Return empty CSS if styling is disabled
            return Response(content="/* Custom styling disabled */", media_type="text/css")
    except Exception as e:
        logger.error(f"Failed to get styling settings: {e}")
        # Return default CSS if database query fails
        return Response(content="/* Error loading custom styling - using defaults */", media_type="text/css")
    
    # Generate CSS custom properties
    css_content = f"""
/* Dynamic styling generated from admin settings */
:root {{
    --bs-primary: {settings.primary_color};
    --bs-secondary: {settings.secondary_color};
    --bs-success: {settings.success_color};
    --bs-danger: {settings.danger_color};
    --bs-warning: {settings.warning_color};
    --bs-info: {settings.info_color};
    --bs-light: {settings.light_color};
    --bs-dark: {settings.dark_color};
    
    --bs-body-bg: {settings.body_bg_color};
    --bs-body-color: {settings.text_color};
    --bs-link-color: {settings.link_color};
    --bs-link-hover-color: {settings.link_hover_color};
    
    --custom-font-family: {settings.font_family};
    --custom-heading-font-family: {settings.heading_font_family or settings.font_family};
    
    --navbar-bg-color: {settings.navbar_bg_color};
    --navbar-text-color: {settings.navbar_text_color};
}}

/* Apply custom font families */
body {{
    font-family: var(--custom-font-family), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 
                 "Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", 
                 "Segoe UI Symbol", "Noto Emoji", sans-serif !important;
    background-color: var(--bs-body-bg) !important;
    color: var(--bs-body-color) !important;
}}

h1, h2, h3, h4, h5, h6 {{
    font-family: var(--custom-heading-font-family), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, 
                 "Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", 
                 "Segoe UI Symbol", "Noto Emoji", sans-serif !important;
}}

/* Navbar styling */
.navbar {{
    background-color: var(--navbar-bg-color) !important;
}}

.navbar .navbar-brand,
.navbar .nav-link,
.navbar .navbar-text {{
    color: var(--navbar-text-color) !important;
}}

.navbar .nav-link:hover {{
    color: var(--bs-link-hover-color) !important;
}}

/* Logo styling */
.navbar-brand img {{
    max-height: {settings.logo_max_height}px;
    height: auto;
    width: auto;
}}

.login-logo {{
    max-height: {settings.login_logo_max_height}px;
    height: auto;
    width: auto;
    margin-bottom: 1rem;
}}

/* Bootstrap component overrides */
.btn-primary {{
    background-color: var(--bs-primary) !important;
    border-color: var(--bs-primary) !important;
}}

.btn-primary:hover {{
    background-color: color-mix(in srgb, var(--bs-primary) 85%, black) !important;
    border-color: color-mix(in srgb, var(--bs-primary) 85%, black) !important;
}}

.btn-secondary {{
    background-color: var(--bs-secondary) !important;
    border-color: var(--bs-secondary) !important;
}}

.btn-success {{
    background-color: var(--bs-success) !important;
    border-color: var(--bs-success) !important;
}}

.btn-danger {{
    background-color: var(--bs-danger) !important;
    border-color: var(--bs-danger) !important;
}}

.btn-warning {{
    background-color: var(--bs-warning) !important;
    border-color: var(--bs-warning) !important;
}}

.btn-info {{
    background-color: var(--bs-info) !important;
    border-color: var(--bs-info) !important;
}}

/* Login page customization */
{f'''
#login-form-container {{
    background-color: {settings.login_bg_color} !important;
}}
''' if settings.login_bg_color else ''}

{f'''
#login-form {{
    background-color: {settings.login_card_bg_color} !important;
    padding: 2rem;
    border-radius: 0.5rem;
    box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.1);
}}
''' if settings.login_card_bg_color else ''}

/* Custom CSS from admin */
{settings.custom_css or ''}
"""
    
    return Response(content=css_content, media_type="text/css")


@router.get("/public-info")
def get_public_styling_info(
    db: Session = Depends(get_db)
):
    """Get public styling information (no authentication required)"""
    try:
        settings = get_styling_settings(db)
        
        return {
            "enabled": settings.enabled,
            "navbar_brand_text": settings.navbar_brand_text,
            "logo_path": settings.logo_path if settings.enabled else None,
            "logo_alt_text": settings.logo_alt_text if settings.enabled else "Company Logo",
            "logo_max_height": settings.logo_max_height if settings.enabled else 50,
            "login_logo_max_height": settings.login_logo_max_height if settings.enabled else 100,
            "show_logo_in_navbar": settings.show_logo_in_navbar if settings.enabled else True,
            "show_logo_on_login": settings.show_logo_on_login if settings.enabled else True
        }
    except Exception as e:
        logger.error(f"Failed to get public styling info: {e}")
        # Return safe defaults if database query fails
        return {
            "enabled": False,
            "navbar_brand_text": "Booking System",
            "logo_path": None,
            "logo_alt_text": "Company Logo",
            "logo_max_height": 50,
            "login_logo_max_height": 100,
            "show_logo_in_navbar": True,
            "show_logo_on_login": True
        }


@router.get("/preview-styles.css")
def get_preview_styles(
    request: Request,
    # Accept all styling parameters for preview
    primary_color: Optional[str] = None,
    secondary_color: Optional[str] = None,
    success_color: Optional[str] = None,
    danger_color: Optional[str] = None,
    warning_color: Optional[str] = None,
    info_color: Optional[str] = None,
    light_color: Optional[str] = None,
    dark_color: Optional[str] = None,
    body_bg_color: Optional[str] = None,
    text_color: Optional[str] = None,
    link_color: Optional[str] = None,
    link_hover_color: Optional[str] = None,
    font_family: Optional[str] = None,
    heading_font_family: Optional[str] = None,
    navbar_bg_color: Optional[str] = None,
    navbar_text_color: Optional[str] = None,
    logo_max_height: Optional[int] = None,
    login_logo_max_height: Optional[int] = None,
    login_bg_color: Optional[str] = None,
    login_card_bg_color: Optional[str] = None,
    custom_css: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Generate preview CSS with temporary settings"""
    # Get current settings as base
    settings = get_styling_settings(db)
    
    # Override with preview parameters
    preview_settings = {
        'primary_color': primary_color or settings.primary_color,
        'secondary_color': secondary_color or settings.secondary_color,
        'success_color': success_color or settings.success_color,
        'danger_color': danger_color or settings.danger_color,
        'warning_color': warning_color or settings.warning_color,
        'info_color': info_color or settings.info_color,
        'light_color': light_color or settings.light_color,
        'dark_color': dark_color or settings.dark_color,
        'body_bg_color': body_bg_color or settings.body_bg_color,
        'text_color': text_color or settings.text_color,
        'link_color': link_color or settings.link_color,
        'link_hover_color': link_hover_color or settings.link_hover_color,
        'font_family': font_family or settings.font_family,
        'heading_font_family': heading_font_family or settings.heading_font_family or settings.font_family,
        'navbar_bg_color': navbar_bg_color or settings.navbar_bg_color,
        'navbar_text_color': navbar_text_color or settings.navbar_text_color,
        'logo_max_height': logo_max_height or settings.logo_max_height,
        'login_logo_max_height': login_logo_max_height or settings.login_logo_max_height,
        'login_bg_color': login_bg_color or settings.login_bg_color,
        'login_card_bg_color': login_card_bg_color or settings.login_card_bg_color,
        'custom_css': custom_css or settings.custom_css,
    }
    
    # Generate preview CSS (similar to dynamic styles but with preview values)
    css_content = f"""
/* Preview styling */
:root {{
    --bs-primary: {preview_settings['primary_color']};
    --bs-secondary: {preview_settings['secondary_color']};
    --bs-success: {preview_settings['success_color']};
    --bs-danger: {preview_settings['danger_color']};
    --bs-warning: {preview_settings['warning_color']};
    --bs-info: {preview_settings['info_color']};
    --bs-light: {preview_settings['light_color']};
    --bs-dark: {preview_settings['dark_color']};
    
    --bs-body-bg: {preview_settings['body_bg_color']};
    --bs-body-color: {preview_settings['text_color']};
    --bs-link-color: {preview_settings['link_color']};
    --bs-link-hover-color: {preview_settings['link_hover_color']};
    
    --custom-font-family: {preview_settings['font_family']};
    --custom-heading-font-family: {preview_settings['heading_font_family']};
    
    --navbar-bg-color: {preview_settings['navbar_bg_color']};
    --navbar-text-color: {preview_settings['navbar_text_color']};
}}

/* Apply custom font families */
body {{
    font-family: var(--custom-font-family), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    background-color: var(--bs-body-bg) !important;
    color: var(--bs-body-color) !important;
}}

h1, h2, h3, h4, h5, h6 {{
    font-family: var(--custom-heading-font-family), -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}}

/* Preview styles */
{preview_settings['custom_css'] or ''}
"""
    
    return Response(content=css_content, media_type="text/css")


@router.post("/reset-to-defaults")
def reset_to_defaults(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin_user)
):
    """Reset styling settings to Bootstrap defaults"""
    logger.info("Resetting styling settings to defaults")
    
    settings = get_styling_settings(db)
    
    # Remove logo file if exists
    if settings.logo_path:
        file_path = Path("static") / settings.logo_path.lstrip("/static/")
        if file_path.exists():
            file_path.unlink()
    
    # Reset all settings to defaults
    defaults = StylingSettings()
    for column in StylingSettings.__table__.columns:
        if column.name != 'id':  # Don't reset the ID
            setattr(settings, column.name, getattr(defaults, column.name))
    
    db.commit()
    db.refresh(settings)
    
    logger.info("Styling settings reset to defaults")
    return {"message": "Styling settings reset to defaults"}
