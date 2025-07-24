#!/usr/bin/env python3
"""Check OIDC provider configuration in database"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from booking.database import get_db
from booking.models import OIDCProvider
import requests

def check_oidc_providers():
    """Check OIDC providers in database and test their endpoints"""
    db = next(get_db())
    
    providers = db.query(OIDCProvider).all()
    
    if not providers:
        print("No OIDC providers found in database")
        return
    
    print(f"Found {len(providers)} OIDC provider(s):")
    print()
    
    for provider in providers:
        print(f"=== Provider: {provider.display_name or provider.issuer} ===")
        print(f"Issuer: {provider.issuer}")
        print(f"Display Name: {provider.display_name}")
        print(f"Client ID: {provider.client_id}")
        print(f"Client Secret: {'***' if provider.client_secret else 'None'}")
        print(f"Well-known URL: {provider.well_known_url}")
        print(f"Scopes: {provider.scopes}")
        print()
        
        # Test well-known endpoint
        if provider.well_known_url:
            print(f"Testing well-known URL: {provider.well_known_url}")
            try:
                response = requests.get(provider.well_known_url, timeout=10)
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    well_known = response.json()
                    
                    # Check key endpoints
                    key_endpoints = [
                        'issuer', 'authorization_endpoint', 'token_endpoint', 
                        'userinfo_endpoint', 'jwks_uri', 'end_session_endpoint'
                    ]
                    
                    print("Key endpoints:")
                    for endpoint in key_endpoints:
                        if endpoint in well_known:
                            print(f"  ✓ {endpoint}: {well_known[endpoint]}")
                        else:
                            print(f"  ❌ {endpoint}: Missing")
                    
                    # Test JWKS endpoint if available
                    jwks_uri = well_known.get('jwks_uri')
                    if jwks_uri:
                        print(f"\nTesting JWKS endpoint: {jwks_uri}")
                        try:
                            jwks_response = requests.get(jwks_uri, timeout=10)
                            print(f"JWKS Status: {jwks_response.status_code}")
                            
                            if jwks_response.status_code == 200:
                                jwks = jwks_response.json()
                                if 'keys' in jwks:
                                    print(f"JWKS Keys: {len(jwks['keys'])} found")
                                    for i, key in enumerate(jwks['keys']):
                                        kid = key.get('kid', f'key-{i}')
                                        kty = key.get('kty', 'unknown')
                                        use = key.get('use', 'unspecified')
                                        alg = key.get('alg', 'unspecified')
                                        print(f"  Key {i+1}: kid={kid}, kty={kty}, use={use}, alg={alg}")
                                else:
                                    print("❌ No 'keys' field in JWKS response")
                                    print(f"JWKS content: {jwks}")
                            else:
                                print(f"❌ JWKS request failed: {jwks_response.text[:200]}")
                        except Exception as e:
                            print(f"❌ JWKS request error: {e}")
                
                else:
                    print(f"❌ Well-known request failed: {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ Well-known request error: {e}")
        
        print("-" * 50)
        print()

if __name__ == "__main__":
    check_oidc_providers()
