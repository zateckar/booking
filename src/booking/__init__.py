from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import asyncio
import logging
import httpx
from urllib.parse import unquote

from . import models
from .database import engine, get_db
from .routers.admin import router as admin_router
from .routers import bookings, users, parking_lots, auth
from .oidc import oauth, process_auth_response
from .scheduler import start_scheduler, stop_scheduler
from .logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger("main")

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Add session middleware for OIDC authentication
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-change-in-production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(bookings.router)
app.include_router(users.router)
app.include_router(parking_lots.router)
app.include_router(auth.router)
app.include_router(admin_router, prefix="/api/admin")


@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup"""
    logger.info("Application starting up")
    await start_scheduler()
    logger.info("Application startup completed")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background tasks on application shutdown"""
    try:
        logger.info("Application shutting down")
        await stop_scheduler()
        logger.info("Application shutdown completed")
    except Exception as e:
        # During shutdown, logging might fail due to database teardown
        # Use basic print as fallback
        print(f"Warning: Error during shutdown: {e}")
        try:
            await stop_scheduler()
        except Exception as scheduler_error:
            print(f"Warning: Error stopping scheduler: {scheduler_error}")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Landing page with smart OIDC provider handling"""
    logger.debug("Serving landing page")
    
    # Get available OIDC providers
    db = next(get_db())
    providers = db.query(models.OIDCProvider).all()
    db.close()
    
    if not providers:
        # No OIDC providers configured, redirect to local login
        logger.debug("No OIDC providers found, redirecting to /login")
        return RedirectResponse(url="/login", status_code=302)
    
    elif len(providers) == 1:
        # Only one OIDC provider, redirect automatically
        provider = providers[0]
        login_url = f"/api/login/oidc/{provider.issuer}"
        logger.debug(f"Single OIDC provider found, redirecting to: {login_url}")
        return RedirectResponse(url=login_url, status_code=302)
    
    else:
        # Multiple OIDC providers, show selection page
        logger.debug(f"Multiple OIDC providers found ({len(providers)}), showing selection page")
        provider_data = [
            {
                "issuer": provider.issuer,
                "display_name": provider.display_name or provider.issuer.replace("_", " ").title()
            }
            for provider in providers
        ]
        return templates.TemplateResponse("oidc_selection.html", {
            "request": request, 
            "providers": provider_data
        })


@app.get("/login", response_class=HTMLResponse)
async def local_login_page(request: Request):
    """Local login page"""
    logger.debug("Serving local login page")
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/app", response_class=HTMLResponse)
async def main_app(request: Request):
    """Main application page (for authenticated users)"""
    logger.debug("Serving main application page")
    return templates.TemplateResponse("index.html", {"request": request})


def _get_secure_redirect_uri(request: Request, endpoint: str, **path_params) -> str:
    """
    Generate a secure redirect URI, ensuring HTTPS in production environments.
    
    This function detects if the app is running behind a reverse proxy with HTTPS
    termination and ensures the redirect URI uses HTTPS scheme when appropriate.
    """
    import os
    
    # Generate the base URI
    redirect_uri = str(request.url_for(endpoint, **path_params))
    
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
    if force_https and redirect_uri.startswith("http://"):
        redirect_uri = redirect_uri.replace("http://", "https://", 1)
        logger.info(f"Redirect URI scheme changed to HTTPS for production: {redirect_uri}")
    
    return redirect_uri


@app.get("/api/login/oidc/{provider_name:path}")
async def login_oidc(request: Request, provider_name: str):
    # URL decode the provider name first
    decoded_provider_name = unquote(provider_name)
    logger.info(f"OIDC login attempt for provider: {decoded_provider_name}")
    
    try:
        db = next(get_db())
        provider = (
            db.query(models.OIDCProvider).filter(models.OIDCProvider.issuer == decoded_provider_name).first()
        )
        if not provider:
            logger.warning(f"OIDC provider not found: {decoded_provider_name}")
            raise HTTPException(status_code=404, detail="OIDC provider not found")

        logger.debug(f"Found OIDC provider: {provider.issuer}, well_known_url: {provider.well_known_url}")

        # Register the provider with OAuth client if not already registered
        try:
            client = oauth._clients.get(provider.issuer)
        except (AttributeError, KeyError):
            client = None
            
        if client is None:
            logger.debug(f"Client for provider {provider.issuer} not found, registering.")

            # Some OIDC providers might have non-compliant JWKS (e.g. wrong 'use' parameter).
            # We fetch the server metadata and JWKS manually to inspect and fix it
            # before registering the client. This makes the first login for a provider
            # a bit slower, but it's cached afterward.
            async with httpx.AsyncClient() as http_client:
                try:
                    resp = await http_client.get(provider.well_known_url)
                    resp.raise_for_status()
                    server_metadata = resp.json()

                    jwks_uri = server_metadata.get('jwks_uri')
                    if jwks_uri:
                        resp = await http_client.get(jwks_uri)
                        resp.raise_for_status()
                        jwks = resp.json()
                        # Fix for keys with incorrect 'use' parameter.
                        # By removing 'use', we allow authlib to use the key for signature
                        # verification, bypassing the strict 'sig' check.
                        for key in jwks.get('keys', []):
                            if 'use' in key:
                                del key['use']
                        server_metadata['jwks'] = jwks
                except httpx.HTTPStatusError as e:
                    logger.error(f"Failed to fetch OIDC metadata for {provider.issuer}: {e}")
                    raise HTTPException(status_code=500, detail="Failed to configure OIDC provider.")

            # Manually map server metadata to authlib's init parameters
            # and pass the rest as kwargs to be stored in client.server_metadata.
            # This is necessary because the installed version of authlib does not
            # have a 'server_metadata' parameter in the client constructor.
            config_params = {
                'authorize_url': server_metadata.pop('authorization_endpoint', None),
                'access_token_url': server_metadata.pop('token_endpoint', None),
            }
            # The rest of the metadata (including our fixed 'jwks') will be passed
            # via **kwargs and stored in the client's `server_metadata` attribute.
            config_params.update(server_metadata)

            oauth.register(
                name=provider.issuer,
                client_id=provider.client_id,
                client_secret=provider.client_secret,
                client_kwargs={"scope": provider.scopes},
                token_endpoint_auth_method='client_secret_post',
                **config_params
            )
            client = oauth._clients[provider.issuer]
        
        # Generate secure redirect URI (HTTPS in production)
        redirect_uri = _get_secure_redirect_uri(request, "auth_oidc", provider_name=provider_name)
        logger.debug(f"Redirecting to OIDC provider with redirect_uri: {redirect_uri}")
        return await client.authorize_redirect(request, redirect_uri)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during OIDC login for provider {decoded_provider_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OIDC login failed: {str(e)}")


@app.get("/api/auth/oidc/{provider_name:path}")
async def auth_oidc(request: Request, provider_name: str):
    # URL decode the provider name first
    decoded_provider_name = unquote(provider_name)
    logger.info(f"Processing OIDC auth callback for provider: {decoded_provider_name}")
    
    tokens = await process_auth_response(request, decoded_provider_name)
    if tokens:
        access_token, refresh_token, id_token = tokens
        logger.info(f"Successful OIDC authentication for provider: {decoded_provider_name}")
        response = RedirectResponse(url="/app", status_code=302)
        
        # Set access token cookie
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,  # Keep HttpOnly for security
            path="/",
            samesite="lax",
        )
        
        # Set refresh token cookie with longer expiration
        response.set_cookie(
            key="refresh_token",
            value=f"Bearer {refresh_token}",
            httponly=True,  # Keep HttpOnly for security
            path="/",
            samesite="lax",
            max_age=7 * 24 * 60 * 60  # 7 days to match refresh token expiry
        )
        
        # Store authentication method and OIDC info for logout
        response.set_cookie(
            key="auth_method",
            value="oidc",
            httponly=True,
            path="/",
            samesite="lax",
            max_age=7 * 24 * 60 * 60  # Same as refresh token
        )
        
        response.set_cookie(
            key="oidc_provider",
            value=decoded_provider_name,
            httponly=True,
            path="/",
            samesite="lax",
            max_age=7 * 24 * 60 * 60  # Same as refresh token
        )
        
        # Store ID token for logout (if available)
        if id_token:
            response.set_cookie(
                key="id_token",
                value=id_token,
                httponly=True,
                path="/",
                samesite="lax",
                max_age=7 * 24 * 60 * 60  # Same as refresh token
            )
        
        return response
    
    logger.warning(f"Failed OIDC authentication for provider: {decoded_provider_name}")
    raise HTTPException(status_code=400, detail="Could not log in")


@app.get("/api/oidc/providers")
async def get_public_oidc_providers():
    """Public endpoint to get available OIDC providers for login page"""
    logger.debug("Fetching public OIDC providers")
    
    db = next(get_db())
    providers = db.query(models.OIDCProvider).all()
    
    # Return only the information needed for login buttons (no secrets)
    public_providers = [
        {
            "id": provider.id,
            "issuer": provider.issuer,
            "display_name": provider.display_name or provider.issuer.replace("_", " ").title()
        }
        for provider in providers
    ]
    
    logger.debug(f"Found {len(public_providers)} OIDC providers")
    return public_providers


@app.get("/logout-complete")
async def logout_complete(request: Request):
    """Handle post-logout redirect from OIDC provider"""
    logger.info("Post-logout redirect received from OIDC provider")
    
    # Show a logout completion page or redirect to login
    # For now, redirect to the login page with a success message
    return RedirectResponse(url="/login?logout=success", status_code=302)
