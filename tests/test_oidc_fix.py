#!/usr/bin/env python3
"""
Test script to verify the OIDC client registration fix
"""

from src.booking.oidc import oauth
from src.booking.database import get_db
from src.booking import models

def test_oidc_client_access():
    """Test that we can access OAuth clients without the 'No such client: clients' error"""
    
    # Get OIDC provider from database
    db = next(get_db())
    provider = db.query(models.OIDCProvider).first()
    
    if not provider:
        print("No OIDC providers found in database")
        return False
    
    print(f"Testing with provider: {provider.issuer}")
    
    # Test accessing _clients (should not raise AttributeError)
    try:
        clients_dict = oauth._clients
        print(f"Successfully accessed oauth._clients: {type(clients_dict)}")
        print(f"Current clients: {list(clients_dict.keys())}")
        
        # Test getting a client (should return None if not registered, not raise error)
        client = oauth._clients.get(provider.issuer)
        print(f"Client lookup result: {client}")
        
        return True
        
    except AttributeError as e:
        print(f"AttributeError (this was the original bug): {e}")
        return False
    except Exception as e:
        print(f"Other error: {e}")
        return False

if __name__ == "__main__":
    print("Testing OIDC client access fix...")
    success = test_oidc_client_access()
    print(f"Test {'PASSED' if success else 'FAILED'}")