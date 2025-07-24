"""
Test script to demonstrate OIDC scopes configuration and token logging functionality
"""
import asyncio
import json
import logging
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from src.booking.database import get_db
from src.booking import models, schemas
from src.booking.oidc import register_oidc_provider, log_token_information

# Configure logging to see the token logging in action
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_oidc_provider_crud_with_scopes():
    """Test CRUD operations for OIDC providers with custom scopes"""
    logger.info("Testing OIDC Provider CRUD operations with scopes...")
    
    db = next(get_db())
    
    # Test creating a provider with custom scopes
    test_provider_data = {
        "issuer": "https://test-provider.example.com",
        "client_id": "test-client-id",
        "client_secret": "test-client-secret",
        "well_known_url": "https://test-provider.example.com/.well-known/openid_configuration",
        "scopes": "openid email profile groups department custom:read"
    }
    
    # Create provider
    provider_create = schemas.OIDCProviderCreate(**test_provider_data)
    db_provider = models.OIDCProvider(**provider_create.dict())
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    
    logger.info(f"Created OIDC provider: {db_provider.issuer}")
    logger.info(f"Configured scopes: {db_provider.scopes}")
    
    # Test updating scopes
    update_data = {
        "scopes": "openid email profile groups department custom:read custom:write admin:users"
    }
    provider_update = schemas.OIDCProviderUpdate(**update_data)
    update_fields = provider_update.dict(exclude_unset=True)
    
    for field, value in update_fields.items():
        setattr(db_provider, field, value)
    
    db.commit()
    db.refresh(db_provider)
    
    logger.info(f"Updated scopes for provider {db_provider.issuer}: {db_provider.scopes}")
    
    # Test reading all providers with their scopes
    all_providers = db.query(models.OIDCProvider).all()
    logger.info("All OIDC providers in database:")
    for provider in all_providers:
        logger.info(f"  - {provider.issuer}: '{provider.scopes}'")
    
    # Clean up test provider
    db.delete(db_provider)
    db.commit()
    logger.info("Test provider cleaned up")


def test_token_logging_functionality():
    """Test the enhanced token logging functionality"""
    logger.info("Testing token logging functionality...")
    
    # Mock access token (JWT format)
    mock_access_token = (
        "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsImdyb3VwcyI6WyJkZXZlbG9wZXJzIiwiYWRtaW5zIl0sImRlcGFydG1lbnQiOiJJVCIsImN1c3RvbV9hdHRyaWJ1dGUiOiJjdXN0b21fdmFsdWUiLCJpYXQiOjE1MTYyMzkwMjIsImV4cCI6OTk5OTk5OTk5OX0."
        "mock_signature"
    )
    
    # Mock ID token (JWT format)
    mock_id_token = (
        "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBpY3R1cmUiOiJodHRwczovL2V4YW1wbGUuY29tL2F2YXRhci5qcGciLCJnaXZlbl9uYW1lIjoiSm9obiIsImZhbWlseV9uYW1lIjoiRG9lIiwibG9jYWxlIjoiZW4tVVMiLCJpYXQiOjE1MTYyMzkwMjIsImV4cCI6OTk5OTk5OTk5OX0."
        "mock_signature"
    )
    
    # Mock token response with various information
    mock_token = {
        "access_token": mock_access_token,
        "id_token": mock_id_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "openid email profile groups department custom:read",
        "refresh_token": "mock_refresh_token_12345",
        "userinfo": {
            "sub": "1234567890",
            "name": "John Doe",
            "email": "test@example.com",
            "email_verified": True,
            "picture": "https://example.com/avatar.jpg",
            "given_name": "John",
            "family_name": "Doe",
            "locale": "en-US",
            "groups": ["developers", "admins"],
            "department": "IT",
            "custom_attribute": "custom_value"
        }
    }
    
    # Test logging with different scenarios
    logger.info("=== Testing token logging with full token information ===")
    log_token_information(mock_token, "test-provider.example.com", "test@example.com")
    
    logger.info("\n=== Testing token logging with minimal token information ===")
    minimal_token = {
        "access_token": mock_access_token,
        "token_type": "Bearer",
        "expires_in": 3600
    }
    log_token_information(minimal_token, "minimal-provider.example.com")
    
    logger.info("\n=== Testing token logging with non-JWT tokens ===")
    opaque_token = {
        "access_token": "opaque_access_token_12345",
        "id_token": "opaque_id_token_67890",
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "openid email profile custom:permissions"
    }
    log_token_information(opaque_token, "opaque-provider.example.com")


def test_oidc_provider_registration():
    """Test OIDC provider registration with custom scopes"""
    logger.info("Testing OIDC provider registration with custom scopes...")
    
    db = next(get_db())
    
    # Get an existing provider to test registration
    provider = db.query(models.OIDCProvider).first()
    if provider:
        logger.info(f"Testing registration for provider: {provider.issuer}")
        logger.info(f"Provider scopes: {provider.scopes}")
        
        # Test the registration function (this would normally register with OAuth)
        try:
            # Note: This will fail in test environment due to missing OAuth setup
            # but we can see the logging output
            register_oidc_provider(provider)
            logger.info("Provider registration completed successfully")
        except Exception as e:
            logger.info(f"Provider registration failed as expected in test environment: {e}")
            logger.info("In production, this would register the OAuth client with the configured scopes")
    else:
        logger.info("No OIDC providers found in database for registration test")


async def test_complete_oidc_flow_simulation():
    """Simulate a complete OIDC flow with enhanced logging"""
    logger.info("Simulating complete OIDC authentication flow...")
    
    # This demonstrates what the enhanced logging would show during a real authentication
    provider_name = "test-provider.example.com"
    
    logger.info(f"=== Starting OIDC authentication for provider: {provider_name} ===")
    
    # Simulate the token response that would come from the OIDC provider
    simulated_token_response = {
        "access_token": (
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ1c2VyMTIzIiwiZW1haWwiOiJqb2huLmRvZUBjb21wYW55LmNvbSIsIm5hbWUiOiJKb2huIERvZSIsImdyb3VwcyI6WyJlbXBsb3llZXMiLCJkZXZlbG9wZXJzIl0sImRlcGFydG1lbnQiOiJFbmdpbmVlcmluZyIsInJvbGUiOiJTZW5pb3IgRGV2ZWxvcGVyIiwiY29zdF9jZW50ZXIiOiJFTkctMDAxIiwibWFuYWdlciI6ImphbmUuc21pdGhAY29tcGFueS5jb20iLCJjdXN0b206cGVybWlzc2lvbnMiOlsicmVhZDpwcm9qZWN0cyIsIndyaXRlOmNvZGUiLCJhZG1pbjpkZXYtdG9vbHMiXSwiaWF0IjoxNzA2NzM0ODAwLCJleHAiOjE3MDY3Mzg0MDB9."
            "mock_signature"
        ),
        "id_token": (
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ1c2VyMTIzIiwiZW1haWwiOiJqb2huLmRvZUBjb21wYW55LmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJuYW1lIjoiSm9obiBEb2UiLCJnaXZlbl9uYW1lIjoiSm9obiIsImZhbWlseV9uYW1lIjoiRG9lIiwicGljdHVyZSI6Imh0dHBzOi8vY29tcGFueS5jb20vYXZhdGFycy91c2VyMTIzLmpwZyIsImxvY2FsZSI6ImVuLVVTIiwiem9uZWluZm8iOiJBbWVyaWNhL05ld19Zb3JrIiwiaWF0IjoxNzA2NzM0ODAwLCJleHAiOjE3MDY3Mzg0MDB9."
            "mock_signature"
        ),
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "openid email profile groups department role custom:permissions",
        "refresh_token": "refresh_token_abc123xyz789",
        "userinfo": {
            "sub": "user123",
            "email": "john.doe@company.com",
            "email_verified": True,
            "name": "John Doe",
            "given_name": "John",
            "family_name": "Doe",
            "picture": "https://company.com/avatars/user123.jpg",
            "locale": "en-US",
            "zoneinfo": "America/New_York",
            "groups": ["employees", "developers"],
            "department": "Engineering",
            "role": "Senior Developer",
            "cost_center": "ENG-001",
            "manager": "jane.smith@company.com",
            "custom:permissions": ["read:projects", "write:code", "admin:dev-tools"]
        }
    }
    
    # Log the detailed token information
    log_token_information(simulated_token_response, provider_name, "john.doe@company.com")
    
    logger.info("=== OIDC authentication simulation completed ===")


def main():
    """Run all OIDC tests"""
    logger.info("Starting OIDC scopes and logging tests...")
    
    try:
        # Test CRUD operations with scopes
        test_oidc_provider_crud_with_scopes()
        
        print("\n" + "="*60 + "\n")
        
        # Test token logging functionality
        test_token_logging_functionality()
        
        print("\n" + "="*60 + "\n")
        
        # Test provider registration
        test_oidc_provider_registration()
        
        print("\n" + "="*60 + "\n")
        
        # Test complete flow simulation
        asyncio.run(test_complete_oidc_flow_simulation())
        
        logger.info("All OIDC tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
