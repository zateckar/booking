from authlib.integrations.starlette_client import OAuth
from authlib.common.errors import AuthlibBaseError
from fastapi import Request
import logging
import os
import json
import httpx
from urllib.parse import unquote, urlencode
from jose import jwt
from typing import Dict, Any, Optional

from . import models, security
from .database import get_db
from .claims_service import ClaimsMappingService, ClaimsProcessingError

# Initialize OAuth with proper configuration
oauth = OAuth()
logger = logging.getLogger(__name__)


def get_secure_redirect_uri(request: Request, endpoint: str, **path_params) -> str:
    """
    Generate a secure redirect URI, ensuring HTTPS in production environments.
    
    This function detects if the app is running behind a reverse proxy with HTTPS
    termination and ensures the redirect URI uses HTTPS scheme when appropriate.
    """
    # Generate the base URI using the request's url_for method
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


async def validate_and_fix_jwks(jwks_url: str) -> Dict[str, Any]:
    """
    Enhanced JWKS validation and fixing function that handles various JWKS issues.
    This version ensures each key is unique by its 'kid' and removes the 'use'
    parameter to make it more compatible with authlib, addressing issues with
    providers that send duplicate key IDs (e.g., for 'sig' and 'enc' uses).
    """
    try:
        logger.info(f"Validating and fixing JWKS from: {jwks_url}")

        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()

            # Log raw response for debugging
            raw_content = response.text
            logger.debug(f"Raw JWKS response (first 500 chars): {raw_content[:500]}")

            try:
                jwks = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in JWKS response: {e}")
                raise ValueError(f"JWKS response is not valid JSON: {e}")

            if not isinstance(jwks, dict) or 'keys' not in jwks or not isinstance(jwks['keys'], list):
                raise ValueError("JWKS response must be a JSON object with a 'keys' array.")

            # Track issues and fixes
            issues_found = []
            unique_keys = {}  # Use a dict to store unique keys by their kid

            for i, key in enumerate(jwks['keys']):
                if not isinstance(key, dict):
                    issues_found.append(f"Key {i} is not an object, skipping.")
                    continue

                # Check required fields
                if not all(key.get(f) for f in ['kty', 'kid']):
                    issues_found.append(f"Key {i} missing 'kty' or 'kid', skipping.")
                    continue

                kid = key.get('kid')

                # If we haven't seen this kid before, process and add it.
                # This effectively takes the first key found for a given kid.
                if kid not in unique_keys:
                    key_copy = key.copy()

                    # Remove the 'use' parameter to avoid strict validation issues in authlib.
                    # A key without 'use' can be used for signing.
                    if 'use' in key_copy:
                        original_use = key_copy.pop('use')
                        issues_found.append(f"Removed 'use: {original_use}' from key {kid}.")
                        logger.info(f"Removed 'use' parameter ('{original_use}') from key {kid} to improve compatibility.")

                    unique_keys[kid] = key_copy
                else:
                    issues_found.append(f"Skipping duplicate key with kid '{kid}'.")

            if not unique_keys:
                raise ValueError("No valid keys found in JWKS after validation and deduplication.")

            fixed_keys = list(unique_keys.values())
            fixed_jwks = {'keys': fixed_keys}

            if issues_found:
                logger.warning(f"JWKS validation found and addressed {len(issues_found)} issues: {issues_found}")

            logger.info(f"JWKS validation complete: {len(fixed_keys)} unique, valid keys prepared.")
            return fixed_jwks

    except Exception as e:
        logger.error(f"Failed to validate and fix JWKS from {jwks_url}: {e}")
        raise e


async def ensure_oidc_client_registered(provider: models.OIDCProvider) -> Any:
    """
    Ensures that an OIDC client is registered with authlib, fixing JWKS if necessary.
    This function is idempotent and returns the registered client.
    """
    try:
        # Check if client is already registered
        client = oauth._clients.get(provider.issuer)
        if client:
            logger.debug(f"OIDC client for {provider.issuer} is already registered.")
            return client
    except (AttributeError, KeyError):
        # Client not registered, proceed to register.
        pass

    logger.info(f"Client for provider {provider.issuer} not found. Registering now.")

    try:
        # Fetch server metadata to get all endpoints and JWKS URI
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(provider.well_known_url)
            resp.raise_for_status()
            server_metadata = resp.json()

        jwks_uri = server_metadata.get('jwks_uri')
        if jwks_uri:
            logger.info(f"Fetching and fixing JWKS for {provider.issuer} from {jwks_uri}")
            # Use the robust JWKS validation and fixing function
            fixed_jwks = await validate_and_fix_jwks(jwks_uri)
            server_metadata['jwks'] = fixed_jwks
            # Remove jwks_uri to ensure our fixed jwks is used by authlib
            server_metadata.pop('jwks_uri', None)
        
        oauth.register(
            name=provider.issuer,
            client_id=provider.client_id,
            client_secret=provider.client_secret,
            client_kwargs={"scope": provider.scopes},
            token_endpoint_auth_method='client_secret_post',
            # Unpack the server_metadata dictionary into keyword arguments.
            # This is the method that works with this version of `authlib`
            # to correctly pass the fixed 'jwks' and other parameters,
            # preventing authlib from re-fetching the non-compliant JWKS.
            **server_metadata
        )
        logger.info(f"Successfully registered OIDC client for {provider.issuer}")
        return oauth._clients[provider.issuer]

    except (httpx.HTTPStatusError, ValueError) as e:
        logger.error(f"Failed to configure OIDC provider {provider.issuer}: {e}")
        # Raise a runtime error to be caught by the calling endpoint
        raise RuntimeError(f"Failed to configure OIDC provider {provider.issuer}") from e

def log_token_information(token: Dict[str, Any], provider_name: str, user_email: str = None):
    """Log detailed information about access and ID tokens for debugging and auditing"""
    logger.info(f"OIDC Token received from provider: {provider_name}")
    
    # Log access token information
    if "access_token" in token:
        access_token = token["access_token"]
        logger.info(f"Access token received (length: {len(access_token)} chars)")
        
        # Try to decode access token without verification for logging purposes
        try:
            # Decode without verification to get token content for logging
            decoded_access = jwt.get_unverified_claims(access_token)
            logger.info(f"Access token claims: {json.dumps(decoded_access, indent=2)}")
        except Exception as e:
            logger.debug(f"Could not decode access token for logging: {e}")
            # Log first and last few characters for debugging
            logger.debug(f"Access token sample: {access_token[:20]}...{access_token[-20:]}")
    
    # Log ID token information
    if "id_token" in token:
        id_token = token["id_token"]
        logger.info(f"ID token received (length: {len(id_token)} chars)")
        
        # Try to decode ID token without verification for logging purposes
        try:
            decoded_id = jwt.get_unverified_claims(id_token)
            logger.info(f"ID token claims: {json.dumps(decoded_id, indent=2)}")
        except Exception as e:
            logger.debug(f"Could not decode ID token for logging: {e}")
            # Log first and last few characters for debugging
            logger.debug(f"ID token sample: {id_token[:20]}...{id_token[-20:]}")
    
    # Log token metadata
    token_metadata = {
        "token_type": token.get("token_type"),
        "expires_in": token.get("expires_in"),
        "scope": token.get("scope"),
        "refresh_token_present": "refresh_token" in token,
        "user_email": user_email
    }
    logger.info(f"Token metadata: {json.dumps(token_metadata, indent=2)}")
    
    # Log userinfo if present
    if "userinfo" in token and token["userinfo"]:
        logger.info(f"Userinfo from token: {json.dumps(token['userinfo'], indent=2)}")


async def process_auth_response(request: Request, provider_name: str):

    try:
        # The provider_name is already URL-decoded by the route handler
        logger.debug(f"Processing auth response for provider: '{provider_name}'")
        
        # First, get the provider from database to get the correct issuer name
        db = next(get_db())
        provider = (
            db.query(models.OIDCProvider).filter(models.OIDCProvider.issuer == provider_name).first()
        )
        if not provider:
            raise ValueError(f"OIDC provider '{provider_name}' not found in database")
        
        # Ensure the client is registered, with all the necessary fixes.
        client = await ensure_oidc_client_registered(provider)
        if client is None:
            raise ValueError(f"Failed to register OAuth client for provider '{provider.issuer}'")
        
        # Explicitly construct the redirect_uri to ensure it's HTTPS in production.
        # This is crucial for the token exchange step when behind a reverse proxy.
        redirect_uri = get_secure_redirect_uri(request, "auth_oidc", provider_name=provider_name)

        # Get the authorization token. If this fails, it will raise an exception
        # that will be caught by the main try/except block. The complex fallback
        # logic is no longer needed because the client is now registered correctly.
        token = await client.authorize_access_token(request, redirect_uri=redirect_uri)
        
        # Log detailed token information for debugging and auditing
        log_token_information(token, provider_name)
        
        # Get user info from token or make additional request
        user_info = token.get("userinfo")
        if not user_info:
            try:
                user_info = await client.userinfo(token=token)
                logger.info(f"Retrieved userinfo from userinfo endpoint: {json.dumps(user_info, indent=2)}")
            except Exception as e:
                logger.warning(f"Failed to get userinfo from endpoint: {e}")
        
        if not user_info:
            raise ValueError("No user information received from OIDC provider")
            
        email = user_info.get("email")
        if not email:
            raise ValueError("No email address received from OIDC provider")
        
        # Log final token information with user email
        log_token_information(token, provider_name, email)
        
        # Process OIDC claims using the claims mapping service
        db = next(get_db())
        claims_service = ClaimsMappingService(db)
        
        try:

            # Extract claims from ID token or access token
            token_claims = {}
            if "id_token" in token:
                try:
                    token_claims = jwt.get_unverified_claims(token["id_token"])
                except Exception as e:
                    logger.warning(f"Failed to extract claims from ID token: {e}")
            
            # If no ID token claims, try access token
            if not token_claims and "access_token" in token:
                try:
                    token_claims = jwt.get_unverified_claims(token["access_token"])
                except Exception as e:
                    logger.warning(f"Failed to extract claims from access token: {e}")
            
            # Merge with userinfo
            if user_info:
                token_claims.update(user_info)
            
            logger.info(f"Processing {len(token_claims)} claims for user authentication")
            
            # Get or create user
            user = db.query(models.User).filter(models.User.email == email).first()
            if not user:
                # Create a new user if they don't exist
                logger.info(f"Creating new user from OIDC authentication: {email}")
                user = models.User(
                    email=email,
                    hashed_password=security.get_password_hash(""),  # Set a dummy password
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            else:
                logger.info(f"Existing user authenticated via OIDC: {email}")
            
            # Process claims and update user profile
            is_admin, profile_data = claims_service.process_oidc_claims(token_claims, user.id)
            
            # Update user's admin status based on role mappings
            if user.is_admin != is_admin:
                logger.info(f"Updating admin status for user {email}: {user.is_admin} → {is_admin}")
                user.is_admin = is_admin
                db.commit()
                db.refresh(user)
            
            logger.info(f"Claims processing completed. Profile fields: {list(profile_data.keys())}")
            
        except ClaimsProcessingError as e:
            logger.error(f"Claims processing failed for user {email}: {e}")
            # If claims processing fails due to missing required claims, reject authentication
            db.close()
            return None
        except Exception as e:
            logger.error(f"Unexpected error during claims processing for user {email}: {e}")
            # Continue with basic authentication if claims processing fails unexpectedly
            pass
        
        access_token = security.create_access_token(data={"sub": user.email, "is_admin": user.is_admin})
        refresh_token = security.create_refresh_token(data={"sub": user.email, "is_admin": user.is_admin})
        id_token = token.get("id_token")  # Extract ID token for logout purposes
        logger.info(f"OIDC authentication successful for user: {email} from provider: {provider_name} (admin: {user.is_admin})")
        return access_token, refresh_token, id_token
        
    except Exception as e:
        # Log the error for debugging
        logger.error(f"OIDC authentication failed for provider {provider_name}: {str(e)}")
        return None


async def get_oidc_logout_url(provider_name: str, id_token: Optional[str] = None, post_logout_redirect_uri: Optional[str] = None) -> Optional[str]:
    """
    Generate OIDC logout URL for the specified provider
    
    Args:
        provider_name: The OIDC provider issuer name
        id_token: The ID token received during authentication (optional but recommended)
        post_logout_redirect_uri: Where to redirect after logout (optional)
        
    Returns:
        The logout URL to redirect the user to, or None if provider doesn't support logout
    """

    try:
        logger.info(f"Getting OIDC logout URL for provider: {provider_name}")
        
        # Get provider from database
        db = next(get_db())
        provider = (
            db.query(models.OIDCProvider).filter(models.OIDCProvider.issuer == provider_name).first()
        )
        if not provider:
            logger.warning(f"OIDC provider not found: {provider_name}")
            return None
        
        # Fetch the OIDC provider's well-known configuration to get end_session_endpoint
        async with httpx.AsyncClient() as http_client:
            try:
                resp = await http_client.get(provider.well_known_url)
                resp.raise_for_status()
                well_known_config = resp.json()
                
                end_session_endpoint = well_known_config.get('end_session_endpoint')
                if not end_session_endpoint:
                    logger.warning(f"OIDC provider {provider_name} does not support logout (no end_session_endpoint)")
                    return None
                
                logger.info(f"Found end_session_endpoint for {provider_name}: {end_session_endpoint}")
                
                # Build logout parameters
                logout_params = {}
                
                # Add ID token hint if available (recommended by OIDC spec)
                if id_token:
                    logout_params['id_token_hint'] = id_token
                
                # Add post-logout redirect URI if provided
                if post_logout_redirect_uri:
                    logout_params['post_logout_redirect_uri'] = post_logout_redirect_uri
                
                # Add client_id as some providers require it
                logout_params['client_id'] = provider.client_id
                
                # Construct the logout URL
                if logout_params:
                    logout_url = f"{end_session_endpoint}?{urlencode(logout_params)}"
                else:
                    logout_url = end_session_endpoint
                
                logger.info(f"Generated OIDC logout URL for {provider_name}: {logout_url}")
                return logout_url
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to fetch OIDC well-known config for {provider_name}: {e}")
                return None
            except Exception as e:
                logger.error(f"Error processing OIDC well-known config for {provider_name}: {e}")
                return None
                
    except Exception as e:
        logger.error(f"Error generating OIDC logout URL for {provider_name}: {e}")
        return None

