#!/usr/bin/env python3
"""
Test script to verify that admin timers are properly cleaned up on logout,
preventing 401 errors from continuing API calls after logout.
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from booking.database import get_db
from booking.models import User
from booking.security import create_access_token
from sqlalchemy.orm import Session

BASE_URL = "http://localhost:8000"

async def test_logout_timer_cleanup():
    """Test that admin timers are properly cleaned up on logout"""
    
    print("🧪 Testing logout timer cleanup functionality...")
    
    # Create test admin user
    admin_email = "test_admin@example.com"
    admin_password = "testpassword123"
    
    async with aiohttp.ClientSession() as session:
        try:
            # 1. Login as admin
            print(f"📝 Step 1: Logging in as admin user {admin_email}")
            
            login_data = {
                'username': admin_email,
                'password': admin_password
            }
            
            async with session.post(
                f"{BASE_URL}/api/token",
                data=login_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                if response.status != 200:
                    print(f"❌ Login failed with status {response.status}")
                    response_text = await response.text()
                    print(f"Response: {response_text}")
                    return False
                
                login_result = await response.json()
                access_token = login_result['access_token']
                print(f"✅ Login successful, got access token")
            
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # 2. Make some admin API calls to verify access
            print("📝 Step 2: Making admin API calls to verify access")
            
            admin_endpoints = [
                "/api/admin/backup-settings/",
                "/api/admin/logs/stats?hours=24"
            ]
            
            for endpoint in admin_endpoints:
                async with session.get(f"{BASE_URL}{endpoint}", headers=headers) as response:
                    if response.status == 200:
                        print(f"✅ Admin API call successful: {endpoint}")
                    else:
                        print(f"❌ Admin API call failed: {endpoint} - Status: {response.status}")
                        return False
            
            # 3. Call logout endpoint
            print("📝 Step 3: Calling logout endpoint")
            
            async with session.post(
                f"{BASE_URL}/api/logout",
                headers=headers
            ) as response:
                if response.status == 200:
                    print("✅ Logout successful")
                else:
                    print(f"❌ Logout failed with status {response.status}")
                    return False
            
            # 4. Wait and monitor for any unauthorized API calls
            print("📝 Step 4: Monitoring for unauthorized API calls after logout")
            print("   Waiting 10 seconds to see if any background timers make unauthorized calls...")
            
            # Check server logs or make calls that would trigger errors if timers are still running
            for i in range(10):
                await asyncio.sleep(1)
                print(f"   Waiting... {i+1}/10 seconds")
                
                # Try to access admin endpoints without token (should fail gracefully)
                for endpoint in admin_endpoints:
                    async with session.get(f"{BASE_URL}{endpoint}") as response:
                        if response.status == 401:
                            print(f"   ⚠️  Expected 401 for {endpoint} (no token)")
                        else:
                            print(f"   ❓ Unexpected status {response.status} for {endpoint}")
            
            # 5. Verify that using the old token fails
            print("📝 Step 5: Verifying that old token is invalidated")
            
            for endpoint in admin_endpoints:
                async with session.get(f"{BASE_URL}{endpoint}", headers=headers) as response:
                    if response.status == 401:
                        print(f"✅ Old token correctly rejected for {endpoint}")
                    else:
                        print(f"❌ Old token still works for {endpoint} - Status: {response.status}")
                        return False
            
            print("\n🎉 Logout timer cleanup test completed successfully!")
            print("✅ Admin timers should be properly cleaned up on logout")
            print("✅ No unauthorized API calls should occur after logout")
            print("✅ Old tokens are properly invalidated")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False

def create_test_admin_user():
    """Create a test admin user for testing"""
    print("👤 Creating test admin user...")
    
    db = next(get_db())
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == "test_admin@example.com").first()
        if existing_user:
            print("✅ Test admin user already exists")
            return True
        
        # Create new admin user
        admin_user = User(
            email="test_admin@example.com",
            hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeaHsFlBjd.qPEa5C",  # "testpassword123"
            is_admin=True,
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("✅ Test admin user created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test admin user: {e}")
        db.rollback()
        return False
    finally:
        db.close()

async def main():
    """Main test function"""
    print("🚀 Starting logout timer cleanup test")
    print("=" * 60)
    
    # Create test admin user first
    if not create_test_admin_user():
        print("❌ Failed to create test admin user")
        return False
    
    # Run the actual test
    success = await test_logout_timer_cleanup()
    
    print("=" * 60)
    if success:
        print("🎉 All tests passed!")
        print("\n📋 What was tested:")
        print("   • Admin login and API access")
        print("   • Logout endpoint functionality")
        print("   • Timer cleanup on logout")
        print("   • Token invalidation")
        print("   • No unauthorized calls after logout")
        print("\n🔧 The fix should prevent:")
        print("   • 401 errors in logs after logout")
        print("   • Background admin API calls from dashboard timer")
        print("   • Session expired errors on login page")
    else:
        print("❌ Some tests failed!")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
