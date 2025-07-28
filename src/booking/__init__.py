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

from . import models, oidc
from .database import engine, get_db
from .routers.admin import router as admin_router
from .routers import bookings, users, parking_lots, auth, oidc as oidc_router
from .oidc import initialize_oidc_providers
from .scheduler import start_scheduler, stop_scheduler
from .logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger("main")

# Database tables will be created by create_db_and_tables() in run.py

app = FastAPI()

# Add session middleware for OIDC authentication
import os
session_secret = os.getenv("SESSION_SECRET_KEY", "your-secret-key-change-in-production")
if session_secret == "your-secret-key-change-in-production":
    logger.warning("Using default session secret key. Set SESSION_SECRET_KEY environment variable for production.")

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    same_site="lax",
    https_only=os.getenv("USE_HTTPS", "false").lower() == "true",
)

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
app.include_router(oidc_router.router, prefix="/oidc")
app.include_router(admin_router, prefix="/api/admin")


@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup"""
    logger.info("Application starting up")
    initialize_oidc_providers()
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
    
    # Get available OIDC providers using the new helper function
    providers_data = oidc.get_available_providers()
    
    if not providers_data:
        # No OIDC providers configured, redirect to local login
        logger.debug("No OIDC providers found, redirecting to /login")
        return RedirectResponse(url="/login", status_code=302)
    
    elif len(providers_data) == 1:
        # Only one OIDC provider, redirect automatically
        provider = providers_data[0]
        login_url = f"/oidc/login/{provider['id']}"
        logger.debug(f"Single OIDC provider found, redirecting to: {login_url}")
        return RedirectResponse(url=login_url, status_code=302)
    
    else:
        # Multiple OIDC providers, show selection page
        logger.debug(f"Multiple OIDC providers found ({len(providers_data)}), showing selection page")
        return templates.TemplateResponse("oidc_selection.html", {
            "request": request, 
            "providers": providers_data
        })


@app.get("/login", response_class=HTMLResponse)
async def local_login_page(request: Request):
    """Local login page"""
    logger.debug("Serving local login page")
    
    # Get available OIDC providers using the new helper function
    providers_data = oidc.get_available_providers()
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "providers": providers_data
    })


@app.get("/app", response_class=HTMLResponse)
async def main_app(request: Request):
    """Main application page (for authenticated users)"""
    logger.debug("Serving main application page")
    return templates.TemplateResponse("index.html", {"request": request})




@app.get("/logout-complete")
async def logout_complete(request: Request):
    """Handle post-logout redirect from OIDC provider"""
    logger.info("Post-logout redirect received from OIDC provider")
    
    # Show a logout completion page or redirect to login
    # For now, redirect to the login page with a success message
    return RedirectResponse(url="/login?logout=success", status_code=302)


@app.get("/debug/session-test")
async def session_test(request: Request):
    """Debug endpoint to test session functionality"""
    import secrets
    from datetime import datetime
    
    # Generate a test value
    test_value = secrets.token_urlsafe(16)
    
    # Store in session
    request.session['test_value'] = test_value
    request.session['test_timestamp'] = str(datetime.now())
    
    # Try to retrieve immediately
    retrieved_value = request.session.get('test_value')
    retrieved_timestamp = request.session.get('test_timestamp')
    
    return {
        "session_test": "ok",
        "stored_value": test_value,
        "retrieved_value": retrieved_value,
        "stored_timestamp": retrieved_timestamp,
        "session_keys": list(request.session.keys()),
        "session_id": getattr(request.session, 'session_id', 'unknown'),
        "values_match": test_value == retrieved_value,
        "session_secret_set": bool(os.getenv("SESSION_SECRET_KEY")),
        "use_https": os.getenv("USE_HTTPS", "false").lower() == "true"
    }
