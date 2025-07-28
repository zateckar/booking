from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import logging

from .. import oidc, models, security
from ..database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/login/{provider_id}")
async def oidc_login(request: Request, provider_id: int, db: Session = Depends(get_db)):
    """
    Redirects the user to the OIDC provider for authentication.
    """
    try:
        # Verify provider exists
        provider = db.query(models.OIDCProvider).filter(models.OIDCProvider.id == provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail="OIDC provider not found")
        
        # Start OIDC flow
        redirect_response = await oidc.start_oidc_flow(request, provider_id)
        return redirect_response
        
    except Exception as e:
        logger.error(f"OIDC login error for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start OIDC authentication")


@router.get("/callback/{provider_name}")
async def oidc_callback(
    request: Request, 
    provider_name: str,
    state: str = Query(None),
    code: str = Query(None),
    error: str = Query(None)
):
    """
    Handles the OIDC callback, processes the authentication response,
    and sets session cookies.
    """
    try:
        logger.debug(f"OIDC callback received for provider: {provider_name}")
        logger.debug(f"Callback parameters - state: {state[:8] if state else None}..., code: {'present' if code else 'missing'}, error: {error}")
        
        # Debug session information
        session_state = request.session.get('oidc_state')
        session_provider_id = request.session.get('oidc_provider_id')
        session_provider_name = request.session.get('oidc_provider_name')
        logger.debug(f"Session data - state: {session_state[:8] if session_state else None}..., provider_id: {session_provider_id}, provider_name: {session_provider_name}")
        
        # Check for OAuth error response
        if error:
            logger.error(f"OIDC provider returned error: {error}")
            raise HTTPException(status_code=400, detail=f"OIDC authentication failed: {error}")
        
        if not code:
            logger.error("No authorization code received from OIDC provider")
            raise HTTPException(status_code=400, detail="No authorization code received")
        
        # Generate redirect URI for this callback
        redirect_uri = oidc.get_redirect_uri(provider_name)
        logger.debug(f"Using redirect URI: {redirect_uri}")
        
        # Process the authentication response
        tokens = await oidc.process_auth_response(request, provider_name, redirect_uri, state)
        if not tokens:
            raise HTTPException(status_code=400, detail="OIDC authentication failed")

        access_token, refresh_token, id_token = tokens
        
        # Create response and set cookies
        response = RedirectResponse(url="/app")
        response.set_cookie(
            key="access_token", 
            value=f"Bearer {access_token}", 
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax"
        )
        response.set_cookie(
            key="refresh_token", 
            value=f"Bearer {refresh_token}", 
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax"
        )
        if id_token:
            response.set_cookie(
                key="id_token", 
                value=id_token, 
                httponly=True,
                secure=request.url.scheme == "https",
                samesite="lax"
            )
        response.set_cookie(
            key="auth_method", 
            value="oidc", 
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax"
        )
        response.set_cookie(
            key="oidc_provider", 
            value=provider_name, 
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax"
        )
        
        logger.info(f"OIDC authentication successful for provider: {provider_name}")
        return response

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"OIDC callback error for provider {provider_name}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during OIDC callback")


@router.get("/logout")
async def oidc_logout(request: Request):
    """
    Handle OIDC logout by redirecting to provider's logout endpoint.
    """
    try:
        # Get current session info
        oidc_provider = request.cookies.get("oidc_provider")
        id_token = request.cookies.get("id_token")
        
        if not oidc_provider:
            # No OIDC session, just clear cookies and redirect
            response = RedirectResponse(url="/login")
            response.delete_cookie("access_token")
            response.delete_cookie("refresh_token")
            response.delete_cookie("id_token")
            response.delete_cookie("auth_method")
            response.delete_cookie("oidc_provider")
            return response
        
        # Get OIDC logout URL
        post_logout_redirect_uri = f"{oidc.get_base_url()}/login"
        logout_url = await oidc.get_oidc_logout_url(
            oidc_provider, 
            id_token, 
            post_logout_redirect_uri
        )
        
        # Create response to clear local cookies
        if logout_url:
            response = RedirectResponse(url=logout_url)
        else:
            # Fallback if provider doesn't support logout
            response = RedirectResponse(url="/login")
        
        # Clear all authentication cookies
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        response.delete_cookie("id_token")
        response.delete_cookie("auth_method")
        response.delete_cookie("oidc_provider")
        
        logger.info(f"OIDC logout initiated for provider: {oidc_provider}")
        return response
        
    except Exception as e:
        logger.error(f"OIDC logout error: {e}")
        # Even if logout fails, clear local session
        response = RedirectResponse(url="/login")
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        response.delete_cookie("id_token")
        response.delete_cookie("auth_method")
        response.delete_cookie("oidc_provider")
        return response


@router.get("/providers")
async def get_oidc_providers():
    """
    Get list of available OIDC providers for the login page.
    """
    try:
        providers = oidc.get_available_providers()
        return {"providers": providers}
    except Exception as e:
        logger.error(f"Failed to get OIDC providers: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve OIDC providers")
