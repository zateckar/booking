from fastapi import APIRouter, Response, HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging

from ..logging_config import get_logger
from ..database import get_db
from ..security import (
    verify_password, create_access_token, create_refresh_token, 
    verify_refresh_token, is_token_expiring_soon
)
from .. import models

logger = get_logger("routers.auth")

router = APIRouter()


@router.post("/api/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db),
    response: Response = None
):
    """Authenticate user and return access and refresh tokens"""
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Failed login attempt for email: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create both access and refresh tokens
    access_token = create_access_token(data={"sub": user.email, "is_admin": user.is_admin})
    refresh_token = create_refresh_token(data={"sub": user.email, "is_admin": user.is_admin})
    
    # Set authentication method cookie for local login
    if response:
        response.set_cookie(
            key="auth_method",
            value="local",
            httponly=True,
            path="/",
            samesite="lax",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
    
    logger.info(f"Successful login for user: {user.email}")
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/api/refresh")
async def refresh_access_token(request: Request, db: Session = Depends(get_db)):
    """Refresh an access token using a refresh token"""
    # Try to get refresh token from Authorization header
    authorization: str = request.headers.get("Authorization")
    refresh_token = None
    
    if authorization:
        scheme, _, param = authorization.partition(" ")
        if scheme.lower() == "bearer":
            refresh_token = param
    
    # If not in header, try to get it from cookies
    if not refresh_token:
        cookie_refresh_token = request.cookies.get("refresh_token")
        if cookie_refresh_token:
            scheme, _, param = cookie_refresh_token.partition(" ")
            if scheme.lower() == "bearer":
                refresh_token = param
    
    # If not in header or cookies, try to get it from the request body
    if not refresh_token:
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except:
            pass
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify the refresh token
    payload = verify_refresh_token(refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email = payload.get("sub")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create new access token
    new_access_token = create_access_token(data={"sub": user.email, "is_admin": user.is_admin})
    
    logger.info(f"Access token refreshed for user: {user.email}")
    
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }


@router.post("/api/check-token")
def check_token_status(request: Request):
    """Check if the current token is expiring soon"""
    # Try to get token from Authorization header
    authorization: str = request.headers.get("Authorization")
    token = None
    
    if authorization:
        scheme, _, param = authorization.partition(" ")
        if scheme.lower() == "bearer":
            token = param
    
    # If not in header, try to get it from cookies
    if not token:
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            scheme, _, param = cookie_token.partition(" ")
            if scheme.lower() == "bearer":
                token = param
    
    if not token:
        return {"needs_refresh": True, "reason": "No token found"}
    
    # Check if token is expiring soon (within 5 minutes)
    if is_token_expiring_soon(token, buffer_minutes=5):
        return {"needs_refresh": True, "reason": "Token expiring soon"}
    
    return {"needs_refresh": False}


def _get_secure_logout_redirect_uri(request: Request) -> str:
    """
    Generate a secure post-logout redirect URI, ensuring HTTPS in production environments.
    """
    import os
    
    # Build base URL from request
    base_url = str(request.base_url).rstrip('/')
    post_logout_redirect_uri = f"{base_url}/logout-complete"
    
    # Check if we should force HTTPS based on various indicators
    force_https = False
    
    # Method 1: Check for explicit environment variable
    if os.getenv("FORCE_HTTPS_REDIRECTS", "").lower() in ("true", "1", "yes"):
        force_https = True
        logger.debug("Force HTTPS enabled via FORCE_HTTPS_REDIRECTS environment variable")
    
    # Method 2: Check for reverse proxy headers indicating HTTPS termination
    elif request.headers.get("x-forwarded-proto") == "https":
        force_https = True
        logger.debug("HTTPS detected via X-Forwarded-Proto header")
    
    elif request.headers.get("x-forwarded-ssl") == "on":
        force_https = True
        logger.debug("HTTPS detected via X-Forwarded-Ssl header")
    
    # Method 3: Check if running in containerized environment (common production setup)
    elif os.getenv("DOCKER_CONTAINER") or os.path.exists("/.dockerenv"):
        # In container, assume production deployment with HTTPS termination
        # unless explicitly running in development mode
        if os.getenv("ENVIRONMENT", "").lower() not in ("development", "dev", "local"):
            force_https = True
            logger.debug("HTTPS assumed for containerized production deployment")
    
    # Apply HTTPS if determined necessary
    if force_https and post_logout_redirect_uri.startswith("http://"):
        post_logout_redirect_uri = post_logout_redirect_uri.replace("http://", "https://", 1)
        logger.info(f"Post-logout redirect URI scheme changed to HTTPS for production: {post_logout_redirect_uri}")
    
    return post_logout_redirect_uri


@router.post("/api/logout")
async def logout(request: Request, response: Response):
    """Logout endpoint that handles both local and OIDC logout"""
    logger.info("User logout requested")
    
    # Check authentication method from cookies
    auth_method = request.cookies.get("auth_method")
    oidc_provider = request.cookies.get("oidc_provider")
    id_token = request.cookies.get("id_token")
    
    logger.info(f"Logout - auth_method: {auth_method}, oidc_provider: {oidc_provider}")
    
    # Clear all authentication cookies
    cookies_to_clear = ["access_token", "refresh_token", "auth_method", "oidc_provider", "id_token"]
    for cookie_name in cookies_to_clear:
        response.set_cookie(
            key=cookie_name,
            value="",
            httponly=True,
            path="/",
            samesite="lax",
            max_age=0  # Immediate expiration
        )
    
    # If this was an OIDC authentication, return OIDC logout URL
    if auth_method == "oidc" and oidc_provider:
        logger.info(f"OIDC logout requested for provider: {oidc_provider}")
        
        from ..oidc import get_oidc_logout_url
        
        # Build the secure post-logout redirect URI (to our logout completion handler)
        post_logout_redirect_uri = _get_secure_logout_redirect_uri(request)
        
        try:
            oidc_logout_url = await get_oidc_logout_url(
                provider_name=oidc_provider,
                id_token=id_token,
                post_logout_redirect_uri=post_logout_redirect_uri
            )
            
            if oidc_logout_url:
                logger.info(f"Redirecting to OIDC logout URL: {oidc_logout_url}")
                return {"message": "OIDC logout initiated", "redirect_url": oidc_logout_url}
            else:
                logger.warning(f"Could not get OIDC logout URL for provider {oidc_provider}, performing local logout only")
        except Exception as e:
            logger.error(f"Error getting OIDC logout URL: {e}")
            logger.warning("Falling back to local logout only")
    
    logger.info("Local logout completed - cookies cleared")
    return {"message": "Logged out successfully"}
