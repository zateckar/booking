import os
import secrets
from authlib.integrations.starlette_client import OAuth
from fastapi import Request
import logging
import json
from urllib.parse import urlencode, urlparse
from typing import Dict, Any, Optional
from contextlib import contextmanager

from . import models, security
from .database import get_db
from .claims_service import ClaimsMappingService, ClaimsProcessingError

oauth = OAuth()
logger = logging.getLogger(__name__)


def get_base_url() -> str:
    """Get the base URL for the application from environment variables."""
    base_url = os.getenv("BASE_URL")
    if base_url:
        return base_url.rstrip("/")
    
    # Fallback for development
    host = os.getenv("HOST", "localhost")
    port = os.getenv("PORT", "8000")
    scheme = "https" if os.getenv("USE_HTTPS", "false").lower() == "true" else "http"
    
    if port in ["80", "443"]:
        return f"{scheme}://{host}"
    return f"{scheme}://{host}:{port}"


def get_provider_name(provider: models.OIDCProvider) -> str:
    """Generate a consistent provider name for OAuth client registration based on issuer domain only."""
    try:
        import re
        
        parsed = urlparse(provider.issuer)
        domain = parsed.netloc or parsed.path
        
        # Create a safe name using only the domain
        safe_name = domain.replace(".", "_").replace("-", "_")
        
        # Remove any remaining non-ASCII characters and ensure URL safety
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', safe_name)
        
        # Remove consecutive underscores and limit length
        safe_name = re.sub(r'_+', '_', safe_name).strip('_')
        
        return safe_name[:50]  # Limit length
    except Exception as e:
        logger.warning(f"Error generating provider name for issuer {provider.issuer}: {e}")
        # Fallback to just using the ID
        return f"provider_{provider.id}"


def get_redirect_uri(provider_name: str) -> str:
    """Generate the redirect URI for a provider."""
    base_url = get_base_url()
    return f"{base_url}/oidc/callback/{provider_name}"


@contextmanager
def get_db_session():
    """Context manager for database sessions."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


def register_provider(provider: models.OIDCProvider) -> str:
    """Register a single OIDC provider with OAuth client."""
    provider_name = get_provider_name(provider)
    redirect_uri = get_redirect_uri(provider_name)
    
    logger.info(f"Registering OIDC provider: {provider.display_name} (name: {provider_name})")
    logger.debug(f"Provider config - Issuer: {provider.issuer}, Redirect URI: {redirect_uri}")
    
    # Register with redirect_uri - this is the standard authlib pattern
    oauth.register(
        name=provider_name,
        client_id=provider.client_id,
        client_secret=provider.client_secret,
        server_metadata_url=provider.well_known_url,
        client_kwargs={"scope": provider.scopes},
        redirect_uri=redirect_uri
    )
    
    return provider_name


def unregister_provider(provider_name: str):
    """Unregister an OIDC provider from OAuth client."""
    try:
        # Remove from oauth registry if it exists
        if hasattr(oauth._clients, 'pop'):
            oauth._clients.pop(provider_name, None)
        logger.info(f"Unregistered OIDC provider: {provider_name}")
    except Exception as e:
        logger.warning(f"Error unregistering provider {provider_name}: {e}")


def initialize_oidc_providers():
    """
    Load all OIDC providers from the database and register them with Authlib.
    This should be called at application startup.
    """
    with get_db_session() as db:
        try:
            providers = db.query(models.OIDCProvider).all()
            logger.info(f"Initializing {len(providers)} OIDC providers")
            
            for provider in providers:
                try:
                    register_provider(provider)
                except Exception as e:
                    logger.error(f"Failed to register provider {provider.display_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to initialize OIDC providers: {e}")


def refresh_provider_registration(provider_id: int):
    """
    Refresh the registration of a specific provider.
    Used when provider configuration is updated.
    """
    with get_db_session() as db:
        try:
            provider = db.query(models.OIDCProvider).filter(models.OIDCProvider.id == provider_id).first()
            if not provider:
                logger.warning(f"Provider with ID {provider_id} not found for refresh")
                return
            
            # Unregister old registration (try multiple possible names)
            new_name = get_provider_name(provider)
            unregister_provider(new_name)
            unregister_provider(provider.issuer)  # Legacy name format
            
            # Also try to unregister old combined format (domain_displayname)
            try:
                import re
                import unicodedata
                parsed = urlparse(provider.issuer)
                domain = parsed.netloc or parsed.path
                display_name = provider.display_name
                display_name = unicodedata.normalize('NFD', display_name)
                display_name = ''.join(c for c in display_name if unicodedata.category(c) != 'Mn')
                old_combined_name = f"{domain}_{display_name}".replace(" ", "_").replace(".", "_")
                old_combined_name = re.sub(r'[^a-zA-Z0-9_-]', '_', old_combined_name)
                old_combined_name = re.sub(r'_+', '_', old_combined_name).strip('_')[:50]
                unregister_provider(old_combined_name)
            except Exception as e:
                logger.debug(f"Could not generate old combined name for cleanup: {e}")
            
            # Register with new configuration
            new_name = register_provider(provider)
            logger.info(f"Refreshed provider registration: {provider.display_name} -> {new_name}")
            
        except Exception as e:
            logger.error(f"Failed to refresh provider {provider_id}: {e}")


def remove_provider_registration(provider_id: int, provider_display_name: str = None):
    """
    Remove provider registration when provider is deleted.
    """
    try:
        # Try to unregister by generating the expected name
        if provider_display_name:
            # Generate name as it would have been created
            fake_provider = type('obj', (object,), {
                'id': provider_id,
                'display_name': provider_display_name,
                'issuer': f"https://example.com/{provider_id}"  # Fallback
            })
            provider_name = get_provider_name(fake_provider)
            unregister_provider(provider_name)
        
        # Also try legacy formats
        unregister_provider(f"provider_{provider_id}")
        logger.info(f"Removed provider registration for ID {provider_id}")
        
    except Exception as e:
        logger.error(f"Failed to remove provider registration {provider_id}: {e}")


def generate_state_token() -> str:
    """Generate a secure state token for CSRF protection."""
    return secrets.token_urlsafe(32)


def log_token_information(token: Dict[str, Any], provider_name: str, user_email: str = None):
    """Log detailed information about the token for debugging and auditing."""
    logger.info(f"OIDC token received from provider: {provider_name}")
    
    # Log id_token claims if available
    if "id_token" in token:
        try:
            id_token_claims = token.get("userinfo", {})
            logger.debug(f"ID token claims: {json.dumps(id_token_claims, indent=2)}")
        except Exception as e:
            logger.debug(f"Could not decode ID token for logging: {e}")

    # Log token metadata (without sensitive data)
    token_metadata = {
        "token_type": token.get("token_type"),
        "expires_in": token.get("expires_in"),
        "scope": token.get("scope"),
        "user_email": user_email,
    }
    logger.info(f"Token metadata: {json.dumps(token_metadata, indent=2)}")


async def start_oidc_flow(request: Request, provider_id: int, state: str = None):
    """
    Start the OIDC authentication flow for a specific provider.
    Returns the authorization redirect response.
    """
    with get_db_session() as db:
        provider = db.query(models.OIDCProvider).filter(models.OIDCProvider.id == provider_id).first()
        if not provider:
            raise ValueError(f"OIDC provider with ID {provider_id} not found")
        
        provider_name = get_provider_name(provider)
        redirect_uri = get_redirect_uri(provider_name)
        
        client = oauth.create_client(provider_name)
        if not client:
            raise ValueError(f"OIDC provider '{provider_name}' not configured")
        
        # Generate state token if not provided
        if not state:
            state = generate_state_token()
        
        # Store state and provider info in session for validation
        if not hasattr(request, 'session'):
            raise ValueError("Session middleware not available")
        
        # Debug session before storing
        logger.debug(f"Session before storing - keys: {list(request.session.keys())}, id: {getattr(request.session, 'session_id', 'unknown')}")
        
        # Store state information
        request.session['oidc_state'] = state
        request.session['oidc_provider_id'] = provider_id
        request.session['oidc_provider_name'] = provider_name
        
        # Force session save to ensure persistence
        if hasattr(request.session, 'save'):
            request.session.save()
        
        # Debug session after storing
        logger.debug(f"Session after storing - keys: {list(request.session.keys())}")
        logger.debug(f"Stored state verification: {request.session.get('oidc_state', 'NOT_FOUND')[:8]}...")
        
        logger.info(f"Starting OIDC flow for provider: {provider.display_name} (state: {state[:8]}...)")
        logger.debug(f"Stored session state: {state}, provider_id: {provider_id}, provider_name: {provider_name}")
        logger.debug(f"Redirect URI: {redirect_uri}")
        
        return await client.authorize_redirect(
            request, 
            redirect_uri,
            state=state
        )


async def process_auth_response(request: Request, provider_name: str, redirect_uri: str, state: str = None):
    """
    Process the OIDC authentication response with state validation.
    """
    try:
        logger.debug(f"Processing auth response for provider: '{provider_name}'")
        
        # Debug session information at callback
        logger.debug(f"Callback session keys: {list(request.session.keys())}")
        logger.debug(f"Callback session id: {getattr(request.session, 'session_id', 'unknown')}")
        logger.debug(f"Received state parameter: {state[:8] if state else None}...")
        
        # Get all session data for debugging
        stored_state = request.session.get('oidc_state')
        stored_provider_id = request.session.get('oidc_provider_id')
        stored_provider_name = request.session.get('oidc_provider_name')
        
        logger.debug(f"Session stored state: {stored_state[:8] if stored_state else None}...")
        logger.debug(f"Session stored provider_id: {stored_provider_id}")
        logger.debug(f"Session stored provider_name: {stored_provider_name}")
        
        # Validate state parameter for CSRF protection
        if stored_state != state:
            logger.error(f"State mismatch: expected '{stored_state}', got '{state}'")
            logger.error(f"Session data available: {dict(request.session)}")
            
            # If no state stored in session, this is likely a session persistence issue
            if stored_state is None:
                logger.error("CRITICAL: No state found in session - possible session middleware issue")
                logger.error("Check that SESSION_SECRET_KEY environment variable is set")
                logger.error("Check that session middleware is properly configured")
                
            raise ValueError("Invalid state parameter - possible CSRF attack or session configuration issue")
        
        # Clear state from session
        request.session.pop('oidc_state', None)
        provider_id = request.session.pop('oidc_provider_id', None)
        
        # Let authlib handle the token exchange
        client = oauth.create_client(provider_name)
        if not client:
            raise ValueError(f"OIDC provider '{provider_name}' not found or configured")
        
        token = await client.authorize_access_token(request)
        
        # Authlib automatically fetches userinfo and attaches it to the token
        user_info = token.get("userinfo")
        if not user_info:
            raise ValueError("No user information received from OIDC provider")
            
        email = user_info.get("email")
        if not email:
            raise ValueError("No email address received from OIDC provider")

        log_token_information(token, provider_name, email)
        
        with get_db_session() as db:
            # Get or create user
            user = db.query(models.User).filter(models.User.email == email).first()
            if not user:
                logger.info(f"Creating new user from OIDC authentication: {email}")
                user = models.User(email=email, hashed_password=security.get_password_hash(""))
                db.add(user)
                db.commit()
                db.refresh(user)
            else:
                logger.info(f"Existing user authenticated via OIDC: {email}")
            
            # Process claims and update user profile
            try:
                claims_service = ClaimsMappingService(db)
                is_admin, _ = claims_service.process_oidc_claims(user_info, user.id)
                if user.is_admin != is_admin:
                    logger.info(f"Updating admin status for user {email}: {user.is_admin} -> {is_admin}")
                    user.is_admin = is_admin
                    db.commit()
                    db.refresh(user)
            except ClaimsProcessingError as e:
                logger.warning(f"Claims processing failed for user {email}: {e}")
                # Continue without claims processing in case of error
            
            access_token = security.create_access_token(data={"sub": user.email, "is_admin": user.is_admin})
            refresh_token = security.create_refresh_token(data={"sub": user.email, "is_admin": user.is_admin})
            id_token = token.get("id_token")
            
            logger.info(f"OIDC authentication successful for user: {email} (admin: {user.is_admin})")
            return access_token, refresh_token, id_token
        
    except Exception as e:
        logger.error(f"OIDC authentication failed for provider {provider_name}: {e}")
        return None


async def get_oidc_logout_url(provider_name: str, id_token: Optional[str] = None, post_logout_redirect_uri: Optional[str] = None) -> Optional[str]:
    """
    Generate OIDC logout URL using provider metadata from authlib.
    """
    try:
        client = oauth.create_client(provider_name)
        if not client:
            logger.warning(f"OIDC provider '{provider_name}' not found or configured")
            return None

        metadata = await client.load_server_metadata()
        end_session_endpoint = metadata.get("end_session_endpoint")

        if not end_session_endpoint:
            logger.warning(f"OIDC provider {provider_name} does not support logout")
            return None

        logout_params = {"client_id": client.client_id}
        if id_token:
            logout_params["id_token_hint"] = id_token
        if post_logout_redirect_uri:
            logout_params["post_logout_redirect_uri"] = post_logout_redirect_uri
        else:
            # Default post-logout redirect
            logout_params["post_logout_redirect_uri"] = f"{get_base_url()}/login"
            
        logout_url = f"{end_session_endpoint}?{urlencode(logout_params)}"
        logger.info(f"Generated OIDC logout URL for {provider_name}")
        return logout_url
        
    except Exception as e:
        logger.error(f"Error generating OIDC logout URL for {provider_name}: {e}")
        return None


def force_refresh_all_providers():
    """
    Force refresh all OIDC provider registrations.
    This will clear all existing registrations and re-register all providers from the database.
    Useful for fixing provider registration issues.
    """
    with get_db_session() as db:
        try:
            # Clear all existing OAuth client registrations
            oauth._clients.clear()
            logger.info("Cleared all existing OIDC provider registrations")
            
            # Re-register all providers from database
            providers = db.query(models.OIDCProvider).all()
            logger.info(f"Force refreshing {len(providers)} OIDC providers")
            
            for provider in providers:
                try:
                    register_provider(provider)
                    logger.info(f"Successfully re-registered provider: {provider.display_name}")
                except Exception as e:
                    logger.error(f"Failed to re-register provider {provider.display_name}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to force refresh OIDC providers: {e}")


def get_available_providers() -> list[Dict[str, Any]]:
    """Get list of available OIDC providers for login page."""
    with get_db_session() as db:
        try:
            providers = db.query(models.OIDCProvider).all()
            return [
                {
                    "id": provider.id,
                    "display_name": provider.display_name,
                    "provider_name": get_provider_name(provider)
                }
                for provider in providers
            ]
        except Exception as e:
            logger.error(f"Failed to get available providers: {e}")
            return []
