#!/usr/bin/env python3
"""Test script to verify JWKS fix for Skoda/VW Group duplicate key IDs"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from booking.oidc import fix_duplicate_jwks
import httpx
import json

async def test_jwks_fix():
    """Test the JWKS fix function with the actual Skoda endpoint"""
    jwks_url = "https://identity.skoda.vwgroup.com/realms/standard/protocol/openid-connect/certs"
    
    print("=== Testing JWKS Fix for Skoda/VW Group ===")
    print(f"JWKS URL: {jwks_url}")
    print()
    
    # First, get the original JWKS directly
    print("=== Original JWKS (with duplicate key IDs) ===")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            original_jwks = response.json()
            
            print(f"Number of keys: {len(original_jwks.get('keys', []))}")
            
            # Check for duplicate key IDs
            kids = {}
            duplicate_kids = []
            
            for i, key in enumerate(original_jwks.get('keys', [])):
                kid = key.get('kid')
                use = key.get('use', 'unknown')
                alg = key.get('alg', 'unknown')
                kty = key.get('kty', 'unknown')
                
                if kid:
                    if kid in kids:
                        duplicate_kids.append((kid, use, alg))
                        print(f"  ❌ DUPLICATE Key {i+1}: kid={kid}, use={use}, alg={alg}, kty={kty}")
                    else:
                        kids[kid] = True
                        print(f"  ✓ Key {i+1}: kid={kid}, use={use}, alg={alg}, kty={kty}")
                else:
                    print(f"  ⚠ Key {i+1}: NO KID, use={use}, alg={alg}, kty={kty}")
            
            print(f"\nFound {len(duplicate_kids)} duplicate key ID(s)")
            
    except Exception as e:
        print(f"❌ Failed to fetch original JWKS: {e}")
        return
    
    print("\n" + "="*60)
    
    # Now test our fix
    print("=== Fixed JWKS (with unique key IDs) ===")
    try:
        fixed_jwks = await fix_duplicate_jwks(jwks_url)
        
        print(f"Number of keys: {len(fixed_jwks.get('keys', []))}")
        
        # Check that all key IDs are now unique
        kids = {}
        duplicate_kids = []
        
        for i, key in enumerate(fixed_jwks.get('keys', [])):
            kid = key.get('kid')
            use = key.get('use', 'unknown')
            alg = key.get('alg', 'unknown')
            kty = key.get('kty', 'unknown')
            
            if kid:
                if kid in kids:
                    duplicate_kids.append((kid, use, alg))
                    print(f"  ❌ STILL DUPLICATE Key {i+1}: kid={kid}, use={use}, alg={alg}, kty={kty}")
                else:
                    kids[kid] = True
                    print(f"  ✓ Key {i+1}: kid={kid}, use={use}, alg={alg}, kty={kty}")
            else:
                print(f"  ⚠ Key {i+1}: NO KID, use={use}, alg={alg}, kty={kty}")
        
        if len(duplicate_kids) == 0:
            print(f"\n✅ SUCCESS: All key IDs are now unique!")
        else:
            print(f"\n❌ FAILED: Still have {len(duplicate_kids)} duplicate key ID(s)")
            
        print("\n=== Key ID Changes Summary ===")
        original_kids = [key.get('kid') for key in original_jwks.get('keys', [])]
        fixed_kids = [key.get('kid') for key in fixed_jwks.get('keys', [])]
        
        for i, (orig_kid, fixed_kid) in enumerate(zip(original_kids, fixed_kids)):
            if orig_kid != fixed_kid:
                key = fixed_jwks['keys'][i]
                use = key.get('use', 'unknown')
                print(f"  Changed: {orig_kid} → {fixed_kid} (use: {use})")
            
    except Exception as e:
        print(f"❌ Failed to fix JWKS: {e}")
        return
    
    print("\n" + "="*60)
    print("=== JWKS Fix Test Completed ===")

if __name__ == "__main__":
    asyncio.run(test_jwks_fix())
