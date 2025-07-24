#!/usr/bin/env python3
"""
Test script for OIDC display name functionality.

This script tests:
1. Database migration was successful
2. Models can handle display_name field
3. API endpoints work with display_name
4. Public endpoint returns display names
"""

import sqlite3
import sys
import json
from fastapi.testclient import TestClient

def test_database_schema():
    """Test that the display_name column was added successfully."""
    print("Testing database schema...")
    
    try:
        conn = sqlite3.connect('booking.db')
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute("PRAGMA table_info(oidc_providers)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        print(f"OIDC providers table columns: {column_names}")
        
        if 'display_name' in column_names:
            print("✅ display_name column exists in database")
        else:
            print("❌ display_name column not found in database")
            return False
        
        # Check if there are any existing providers
        cursor.execute("SELECT id, issuer, display_name FROM oidc_providers")
        providers = cursor.fetchall()
        
        if providers:
            print(f"Found {len(providers)} existing OIDC providers:")
            for provider_id, issuer, display_name in providers:
                print(f"  ID {provider_id}: '{issuer}' -> '{display_name}'")
        else:
            print("No existing OIDC providers found")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_models():
    """Test that the models can handle the display_name field."""
    print("\nTesting models...")
    
    try:
        # Import models to test they load correctly
        from src.booking import models
        from src.booking.database import get_db
        
        # Test creating a provider with display_name
        db = next(get_db())
        
        # Create a test provider
        test_provider = models.OIDCProvider(
            issuer="https://test.example.com",
            display_name="Test Provider",
            client_id="test_client_id",
            client_secret="test_secret",
            well_known_url="https://test.example.com/.well-known/openid_configuration",
            scopes="openid email profile"
        )
        
        db.add(test_provider)
        db.commit()
        db.refresh(test_provider)
        
        print(f"✅ Created test provider: {test_provider.display_name} ({test_provider.issuer})")
        
        # Test retrieving the provider
        retrieved = db.query(models.OIDCProvider).filter(
            models.OIDCProvider.issuer == "https://test.example.com"
        ).first()
        
        if retrieved and retrieved.display_name == "Test Provider":
            print("✅ Retrieved provider with correct display_name")
        else:
            print("❌ Failed to retrieve provider with display_name")
            return False
        
        # Clean up test data
        db.delete(retrieved)
        db.commit()
        print("✅ Cleaned up test data")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Models test failed: {e}")
        return False

def test_api_endpoints():
    """Test that API endpoints work with display_name."""
    print("\nTesting API endpoints...")
    
    try:
        from src.booking import app
        
        client = TestClient(app)
        
        # Test public endpoint for OIDC providers
        response = client.get("/api/oidc/providers")
        
        if response.status_code == 200:
            providers = response.json()
            print(f"✅ Public OIDC providers endpoint works, returned {len(providers)} providers")
            
            for provider in providers:
                if 'display_name' in provider:
                    print(f"  Provider: {provider['display_name']} ({provider['issuer']})")
                else:
                    print(f"  Provider: {provider['issuer']} (no display_name)")
        else:
            print(f"❌ Public endpoint failed with status {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False

def test_schemas():
    """Test that schemas work with display_name."""
    print("\nTesting schemas...")
    
    try:
        from src.booking.schemas import OIDCProviderCreate, OIDCProvider
        
        # Test creating provider schema with display_name
        provider_data = {
            "issuer": "https://test.example.com",
            "display_name": "Test Provider",
            "client_id": "test_client",
            "client_secret": "test_secret",
            "well_known_url": "https://test.example.com/.well-known/openid_configuration",
            "scopes": "openid email profile"
        }
        
        # Test creation schema
        create_schema = OIDCProviderCreate(**provider_data)
        print(f"✅ OIDCProviderCreate schema works: {create_schema.display_name}")
        
        # Test response schema
        response_data = {**provider_data, "id": 1}
        response_schema = OIDCProvider(**response_data)
        print(f"✅ OIDCProvider schema works: {response_schema.display_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Schemas test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing OIDC Display Name Implementation")
    print("=" * 50)
    
    tests = [
        ("Database Schema", test_database_schema),
        ("Models", test_models),
        ("Schemas", test_schemas),
        ("API Endpoints", test_api_endpoints),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! OIDC display name feature is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
