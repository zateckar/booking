from authlib.integrations.starlette_client import OAuth
from authlib.common.errors import AuthlibBaseError
from fastapi import Request
import logging
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


async def fix_duplicate_jwks(jwks_url: str) -> Dict[str, Any]:
    """
    The OIDC provider returns JWKS with duplicate 'kid' values for
    encryption and signing keys, which violates JWKS standards.
    This function fetches the JWKS and fixes duplicate key IDs.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            jwks = response.json()
            
            if 'keys' not in jwks:
                logger.error(f"Invalid JWKS response from {jwks_url}: missing 'keys' field")
                return jwks
            
            # Track seen key IDs and fix duplicates
            seen_kids = {}
            fixed_keys = []
            duplicate_count = 0
            
            for i, key in enumerate(jwks['keys']):
                kid = key.get('kid')
                use = key.get('use', 'unknown')
                alg = key.get('alg', 'unknown')
                
                if kid:
                    if kid in seen_kids:
                        # Duplicate kid found - make it unique by adding use and algorithm suffix
                        original_kid = kid
                        new_kid = f"{kid}_{use}_{alg}"
                        key['kid'] = new_kid
                        duplicate_count += 1
                        logger.info(f"Fixed duplicate JWKS key ID: {original_kid} -> {new_kid} (use: {use}, alg: {alg})")
                    else:
                        seen_kids[kid] = True
                        
                # Validate key has required fields
                if not key.get('kty'):
                    logger.warning(f"JWKS key missing 'kty' field: {key}")
                    continue
                    
                fixed_keys.append(key)
            
            jwks['keys'] = fixed_keys
            logger.info(f"Fixed JWKS with {len(fixed_keys)} keys from {jwks_url} (fixed {duplicate_count} duplicates)")
            return jwks
            
    except Exception as e:
        logger.error(f"Failed to fix JWKS from {jwks_url}: {e}")
        raise e


async def validate_and_fix_jwks(jwks_url: str) -> Dict[str, Any]:
    """
    Enhanced JWKS validation and fixing function that handles various JWKS issues
    including duplicate keys, missing fields, and format problems.
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
            
            if not isinstance(jwks, dict):
                logger.error(f"JWKS response is not a JSON object: {type(jwks)}")
                raise ValueError("JWKS response must be a JSON object")
                
            if 'keys' not in jwks:
                logger.error("JWKS response missing 'keys' field")
                raise ValueError("JWKS response missing 'keys' field")
                
            if not isinstance(jwks['keys'], list):
                logger.error(f"JWKS 'keys' field is not an array: {type(jwks['keys'])}")
                raise ValueError("JWKS 'keys' field must be an array")
            
            # Track issues and fixes
            issues_found = []
            seen_kids = {}
            fixed_keys = []
            
            for i, key in enumerate(jwks['keys']):
                if not isinstance(key, dict):
                    issues_found.append(f"Key {i} is not an object")
                    continue
                
                # Check required fields
                missing_fields = []
                for required_field in ['kty', 'kid']:
                    if not key.get(required_field):
                        missing_fields.append(required_field)
                
                if missing_fields:
                    issues_found.append(f"Key {i} missing required fields: {missing_fields}")
                    logger.warning(f"Skipping JWKS key {i} due to missing fields: {missing_fields}")
                    continue
                
                kid = key.get('kid')
                use = key.get('use', 'unknown')
                alg = key.get('alg', 'unknown')
                kty = key.get('kty')
                
                # Handle duplicate kid
                if kid in seen_kids:
                    original_kid = kid
                    new_kid = f"{kid}_{use}_{alg}"
                    key = key.copy()  # Don't modify original
                    key['kid'] = new_kid
                    issues_found.append(f"Duplicate kid '{original_kid}' fixed to '{new_kid}'")
                    logger.info(f"Fixed duplicate JWKS key ID: {original_kid} -> {new_kid} (use: {use}, alg: {alg})")
                
                seen_kids[kid] = True
                
                # Validate key type specific fields
                if kty == 'RSA':
                    required_rsa_fields = ['n', 'e']
                    missing_rsa = [f for f in required_rsa_fields if not key.get(f)]
                    if missing_rsa:
                        issues_found.append(f"RSA key {kid} missing fields: {missing_rsa}")
                        logger.warning(f"RSA key {kid} missing required fields: {missing_rsa}")
                        continue
                elif kty == 'EC':
                    required_ec_fields = ['x', 'y', 'crv']
                    missing_ec = [f for f in required_ec_fields if not key.get(f)]
                    if missing_ec:
                        issues_found.append(f"EC key {kid} missing fields: {missing_ec}")
                        logger.warning(f"EC key {kid} missing required fields: {missing_ec}")
                        continue
                
                fixed_keys.append(key)
            
            if not fixed_keys:
                raise ValueError("No valid keys found in JWKS after validation")
            
            fixed_jwks = {'keys': fixed_keys}
            
            if issues_found:
                logger.warning(f"JWKS validation found {len(issues_found)} issues: {issues_found}")
            
            logger.info(f"JWKS validation complete: {len(fixed_keys)} valid keys, {len(issues_found)} issues fixed")
            return fixed_jwks
            
    except Exception as e:
        logger.error(f"Failed to validate and fix JWKS from {jwks_url}: {e}")
        raise e


def register_oidc_provider(provider: models.OIDCProvider):
    """Register an OIDC provider with OAuth client using configured scopes"""
    logger.info(f"Registering OIDC provider: {provider.issuer}")
    logger.debug(f"Provider scopes: {provider.scopes}")
    
    oauth.register(
        name=provider.issuer,
        client_id=provider.client_id,
        client_secret=provider.client_secret,
        server_metadata_url=provider.well_known_url,
        client_kwargs={
            "scope": provider.scopes
        }
    )


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
        
        # Check if client is already registered, if not register it with current scopes
        try:
            client = oauth._clients.get(provider.issuer)
        except (AttributeError, KeyError):
            client = None
            
        if client is None:
            logger.info(f"OAuth client not found for provider '{provider.issuer}', registering with scopes: {provider.scopes}")
            register_oidc_provider(provider)
            client = oauth._clients.get(provider.issuer)
            
        if client is None:
            raise ValueError(f"Failed to register OAuth client for provider '{provider.issuer}'")
        
        # Get the authorization token with enhanced error handling for JWKS validation issues
        try:
            token = await client.authorize_access_token(request)
        except Exception as token_error:
            error_msg = str(token_error).lower()
            
            # Check for JWKS validation errors (like duplicate key IDs, invalid format, etc.)
            if ("invalid json web key set" in error_msg or 
                "jwks" in error_msg or 
                "duplicate" in error_msg and "key" in error_msg or
                "json web key" in error_msg or
                "key set" in error_msg):
                
                logger.warning(f"JWKS validation error detected: {str(token_error)}")
                logger.info("Attempting to validate and fix JWKS issues...")
                
                try:
                    # Get the well-known configuration to find the JWKS URL
                    async with httpx.AsyncClient() as http_client:
                        resp = await http_client.get(provider.well_known_url)
                        resp.raise_for_status()
                        well_known = resp.json()
                        jwks_uri = well_known.get('jwks_uri')
                        
                        if jwks_uri:
                            # Use enhanced JWKS validation and fixing
                            logger.info(f"Validating and fixing JWKS from: {jwks_uri}")
                            fixed_jwks = await validate_and_fix_jwks(jwks_uri)
                            
                            # Register client with custom fixed JWKS
                            oauth.register(
                                name=f"{provider.issuer}_validated_jwks",
                                client_id=provider.client_id,
                                client_secret=provider.client_secret,
                                server_metadata_url=provider.well_known_url,
                                client_kwargs={
                                    "scope": provider.scopes
                                },
                                jwks=fixed_jwks  # Use our validated and fixed JWKS
                            )
                            
                            fixed_client = oauth._clients[f"{provider.issuer}_validated_jwks"]
                            token = await fixed_client.authorize_access_token(request)
                            logger.info("Successfully authenticated using validated and fixed JWKS")
                        else:
                            logger.error("No jwks_uri found in well-known configuration")
                            raise token_error
                            
                except Exception as jwks_fix_error:
                    logger.error(f"Failed to validate and fix JWKS: {jwks_fix_error}")
                    
                    # Try the simpler fix as fallback
                    logger.info("Attempting simple JWKS duplicate key fix as fallback...")
                    try:
                        async with httpx.AsyncClient() as http_client:
                            resp = await http_client.get(provider.well_known_url)
                            resp.raise_for_status()
                            well_known = resp.json()
                            jwks_uri = well_known.get('jwks_uri')
                            
                            if jwks_uri:
                                fixed_jwks = await fix_duplicate_jwks(jwks_uri)
                                
                                # Register client with simple fix
                                oauth.register(
                                    name=f"{provider.issuer}_simple_fix",
                                    client_id=provider.client_id,
                                    client_secret=provider.client_secret,
                                    server_metadata_url=provider.well_known_url,
                                    client_kwargs={
                                        "scope": provider.scopes
                                    },
                                    jwks=fixed_jwks
                                )
                                
                                simple_client = oauth._clients[f"{provider.issuer}_simple_fix"]
                                token = await simple_client.authorize_access_token(request)
                                logger.info("Successfully authenticated using simple JWKS fix")
                            else:
                                raise token_error
                    except Exception as simple_fix_error:
                        logger.error(f"Simple JWKS fix also failed: {simple_fix_error}")
                        raise token_error
                    
            elif "use" in error_msg and "not valid" in error_msg:
                logger.warning(f"JWT key validation issue detected: {str(token_error)}")
                # For Skoda/VW Group OIDC, try with different token endpoint method
                try:
                    # Re-register client with different auth method but keep configured scopes
                    oauth.register(
                        name=f"{provider.issuer}_fallback",
                        client_id=provider.client_id,
                        client_secret=provider.client_secret,
                        server_metadata_url=provider.well_known_url,
                        client_kwargs={
                            "scope": provider.scopes
                        },
                        token_endpoint_auth_method='client_secret_basic'
                    )
                    fallback_client = oauth._clients[f"{provider.issuer}_fallback"]
                    token = await fallback_client.authorize_access_token(request)
                except Exception:
                    raise token_error
            else:
                raise token_error
        
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
