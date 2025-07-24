#!/usr/bin/env python3
"""Debug script to check JWKS endpoint and OIDC configuration"""

import requests
import json
import sys
from jose import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import base64

def fetch_jwks():
    """Fetch and analyze JWKS from Skoda/VW Group"""
    jwks_url = "https://identity.skoda.vwgroup.com/realms/standard/protocol/openid-connect/certs"
    well_known_url = "https://identity.skoda.vwgroup.com/realms/standard/.well-known/openid_connect_configuration"
    
    print("=== Fetching OIDC Well-Known Configuration ===")
    try:
        response = requests.get(well_known_url, timeout=10)
        response.raise_for_status()
        well_known = response.json()
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print("Configuration keys:")
        for key in sorted(well_known.keys()):
            print(f"  - {key}: {well_known[key]}")
        print()
    except Exception as e:
        print(f"Error fetching well-known config: {e}")
        return
    
    print("=== Fetching JWKS ===")
    try:
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()
        jwks = response.json()
        
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Response size: {len(response.text)} bytes")
        print()
        
        print("=== JWKS Structure ===")
        print(json.dumps(jwks, indent=2))
        print()
        
        if 'keys' in jwks:
            print(f"Number of keys: {len(jwks['keys'])}")
            for i, key in enumerate(jwks['keys']):
                print(f"\n--- Key {i+1} ---")
                for field, value in key.items():
                    if field in ['n', 'e', 'x', 'y']:  # Long values
                        print(f"  {field}: {value[:50]}..." if len(str(value)) > 50 else f"  {field}: {value}")
                    else:
                        print(f"  {field}: {value}")
                
                # Validate key structure
                validate_jwk(key, i+1)
        else:
            print("ERROR: No 'keys' field found in JWKS!")
            
    except requests.RequestException as e:
        print(f"Network error: {e}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Response content: {response.text[:500]}...")
    except Exception as e:
        print(f"Unexpected error: {e}")

def validate_jwk(key, key_num):
    """Validate individual JWK structure"""
    print(f"    Validating key {key_num}:")
    
    # Check required fields
    required_fields = ['kty']  # Key type is always required
    for field in required_fields:
        if field not in key:
            print(f"    ❌ Missing required field: {field}")
            return
    
    kty = key.get('kty')
    print(f"    ✓ Key type (kty): {kty}")
    
    if kty == 'RSA':
        rsa_required = ['n', 'e']
        for field in rsa_required:
            if field not in key:
                print(f"    ❌ Missing RSA field: {field}")
                return
            else:
                print(f"    ✓ RSA field present: {field}")
        
        # Try to construct RSA public key
        try:
            n = base64.urlsafe_b64decode(key['n'] + '==')  # Add padding
            e = base64.urlsafe_b64decode(key['e'] + '==')  # Add padding
            
            n_int = int.from_bytes(n, 'big')
            e_int = int.from_bytes(e, 'big')
            
            # Create RSA public key
            public_key = rsa.RSAPublicNumbers(e_int, n_int).public_key()
            print(f"    ✓ RSA key validation successful")
            print(f"    ✓ Key size: {public_key.key_size} bits")
            
        except Exception as e:
            print(f"    ❌ RSA key validation failed: {e}")
    
    elif kty == 'EC':
        ec_required = ['crv', 'x', 'y']
        for field in ec_required:
            if field not in key:
                print(f"    ❌ Missing EC field: {field}")
                return
            else:
                print(f"    ✓ EC field present: {field}")
    
    # Check optional but important fields
    optional_fields = ['use', 'alg', 'kid']
    for field in optional_fields:
        if field in key:
            print(f"    ✓ Optional field present: {field} = {key[field]}")
        else:
            print(f"    ⚠ Optional field missing: {field}")

if __name__ == "__main__":
    fetch_jwks()
