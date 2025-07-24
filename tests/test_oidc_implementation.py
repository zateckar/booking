#!/usr/bin/env python3
"""
Test script to verify OIDC implementation and identify issues
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_oidc_endpoints():
    """Test OIDC-related endpoints"""
    print("=== Testing OIDC Implementation (After Fixes) ===\n")
    
    # Test 1: Try to fetch OIDC providers from new public endpoint
    print("1. Testing NEW public OIDC providers endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/oidc/providers")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            providers = response.json()
            print(f"   Found {len(providers)} providers")
            for provider in providers:
                print(f"   - {provider.get('issuer', 'Unknown')} (Display: {provider.get('display_name', 'N/A')})")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Connection error: {e}")
    
    print()
    
    # Test 2: Verify old admin endpoint still requires auth
    print("2. Verifying admin endpoint still requires authentication...")
    try:
        response = requests.get(f"{BASE_URL}/api/admin/oidc/")
        if response.status_code == 401:
            print("   ✓ Admin endpoint properly secured")
        elif response.status_code == 200:
            print("   ⚠ Admin endpoint accessible without auth")
        else:
            print(f"   Unexpected response: {response.status_code}")
    except Exception as e:
        print(f"   Connection error: {e}")
    
    print()
    
    # Test 3: Test OIDC login endpoint
    print("3. Testing OIDC login endpoint...")
    try:
        # Try with a dummy provider name
        response = requests.get(f"{BASE_URL}/api/login/oidc/test-provider", allow_redirects=False)
        print(f"   Status: {response.status_code}")
        if response.status_code == 404:
            print("   ✓ Provider not found (expected if no providers configured)")
        elif response.status_code == 302:
            print("   ✓ Redirect to OIDC provider (good)")
        else:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Connection error: {e}")
    
    print()
    
    # Test 4: Check main page for OIDC login buttons
    print("4. Testing main page...")
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("   ✓ Main page loads successfully")
            if 'oidc-login-buttons' in response.text:
                print("   ✓ OIDC login buttons container found in HTML")
            else:
                print("   ✗ OIDC login buttons container NOT found")
        else:
            print(f"   Error loading main page: {response.status_code}")
    except Exception as e:
        print(f"   Connection error: {e}")

def create_test_oidc_provider():
    """Helper function to create a test OIDC provider for demonstration"""
    print("\n=== Creating Test OIDC Provider ===")
    print("To test OIDC functionality, you need to:")
    print("1. Start the application: python run.py")
    print("2. Login as admin user")
    print("3. Go to Admin -> OIDC tab")
    print("4. Add an OIDC provider with these example values:")
    print("   - Issuer: google")
    print("   - Client ID: your-google-client-id")
    print("   - Client Secret: your-google-client-secret")
    print("   - Well-known URL: https://accounts.google.com/.well-known/openid_configuration")
    print("\nOr for testing with a local provider:")
    print("   - Issuer: keycloak")
    print("   - Client ID: parking-booking")
    print("   - Client Secret: your-secret")
    print("   - Well-known URL: http://localhost:8080/realms/master/.well-known/openid_configuration")

if __name__ == "__main__":
    test_oidc_endpoints()
    create_test_oidc_provider()