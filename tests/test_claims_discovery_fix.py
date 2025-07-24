#!/usr/bin/env python3

"""
Test script to verify the claims discovery functionality works with both JWT tokens and JSON objects
"""

import requests
import json

# Sample JWT token (this is a sample/expired token for testing)
SAMPLE_JWT = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWUsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGVzIjpbImFkbWluIiwidXNlciJdLCJpYXQiOjE1MTYyMzkwMjJ9.invalid"

# Sample JSON claims object
SAMPLE_JSON = {
    "sub": "1234567890",
    "name": "John Doe", 
    "admin": True,
    "email": "test@example.com",
    "roles": ["admin", "user"],
    "iat": 1516239022,
    "exp": 1753012925,
    "iss": "https://identity.skoda.vwgroup.com/realms/standard",
    "aud": ["eai_95f6eaff", "eai-test"],
    "preferred_username": "testuser",
    "display_name": "Test User",
    "department_number": "IT",
    "organization": "TEST ORG"
}

def test_claims_discovery():
    """Test claims discovery with both JWT and JSON formats"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Claims Discovery Functionality")
    print("=" * 50)
    
    # Test data
    test_cases = [
        {
            "name": "JWT Token",
            "data": SAMPLE_JWT,
            "expected_format": "JWT"
        },
        {
            "name": "JSON Claims Object", 
            "data": json.dumps(SAMPLE_JSON),
            "expected_format": "JSON"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 Testing {test_case['name']}...")
        print(f"Expected format: {test_case['expected_format']}")
        
        # Prepare request
        payload = {
            "sample_token": test_case["data"]
        }
        
        print(f"Request payload size: {len(json.dumps(payload))} characters")
        print(f"First 100 chars: {test_case['data'][:100]}...")
        
        try:
            # Make request to claims discovery endpoint
            response = requests.post(
                f"{base_url}/api/admin/claims/claims-discovery",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                discovered_claims = result.get("discovered_claims", {})
                existing_mappings = result.get("existing_mappings", [])
                unmapped_claims = result.get("unmapped_claims", [])
                
                print(f"✅ SUCCESS - Discovered {len(discovered_claims)} claims")
                print(f"   - Existing mappings: {len(existing_mappings)}")
                print(f"   - Unmapped claims: {len(unmapped_claims)}")
                
                if discovered_claims:
                    print("   - Sample discovered claims:")
                    for claim_name, claim_value in list(discovered_claims.items())[:3]:
                        print(f"     • {claim_name}: {claim_value}")
                
                if unmapped_claims:
                    print(f"   - Unmapped claims: {', '.join(unmapped_claims[:5])}")
                    
            else:
                print(f"❌ FAILED - HTTP {response.status_code}")
                try:
                    error_detail = response.json().get("detail", "Unknown error")
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")
                    
        except requests.exceptions.ConnectionError:
            print("❌ FAILED - Cannot connect to server. Is the application running on localhost:8000?")
        except requests.exceptions.Timeout:
            print("❌ FAILED - Request timed out")
        except Exception as e:
            print(f"❌ FAILED - Unexpected error: {e}")

def test_create_claim_mapping():
    """Test creating a claim mapping to verify the database issue is fixed"""
    base_url = "http://localhost:8000"
    
    print(f"\n🔧 Testing Claim Mapping Creation...")
    
    # Test mapping data
    mapping_data = {
        "claim_name": "test_claim",
        "mapped_field_name": "test_field", 
        "mapping_type": "attribute",
        "display_label": "Test Claim",
        "is_required": False,
        "default_value": None,
        "description": "Test mapping for verification",
        "role_admin_values": []
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/admin/claims/claims-mappings",
            json=mapping_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS - Created mapping: {result.get('claim_name')} → {result.get('mapped_field_name')}")
            
            # Clean up - delete the test mapping
            mapping_id = result.get('id')
            if mapping_id:
                delete_response = requests.delete(
                    f"{base_url}/api/admin/claims/claims-mappings/{mapping_id}",
                    timeout=10
                )
                if delete_response.status_code == 200:
                    print("   Cleanup: Test mapping deleted successfully")
                    
        else:
            print(f"❌ FAILED - HTTP {response.status_code}")
            try:
                error_detail = response.json().get("detail", "Unknown error")
                print(f"   Error: {error_detail}")
            except:
                print(f"   Error: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ FAILED - Cannot connect to server. Is the application running on localhost:8000?")
    except Exception as e:
        print(f"❌ FAILED - Unexpected error: {e}")

if __name__ == "__main__":
    print("🚀 Claims Discovery Fix Verification")
    print("This script tests the fixes for the Claims Discovery functionality")
    print("\nMake sure the application is running on localhost:8000 before running this test.")
    print("You may need to authenticate first to access admin endpoints.\n")
    
    # Run tests
    test_claims_discovery()
    test_create_claim_mapping()
    
    print(f"\n📝 Test Summary:")
    print("- Claims discovery should now work with both JWT tokens and JSON objects")
    print("- Claim mapping creation should work without database errors")
    print("- Frontend validation should provide better user guidance")
    print("\nIf any tests failed, check the server logs for more details.")
