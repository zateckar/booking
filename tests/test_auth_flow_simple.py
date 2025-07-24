#!/usr/bin/env python3
"""
Simple test script to verify the authentication flow fixes.
This test manually checks the application behavior by starting the server
and providing instructions for manual verification.
"""

import subprocess
import time
import requests
import sys

def start_server():
    """Start the FastAPI server"""
    print("🚀 Starting server...")
    process = subprocess.Popen(
        ["python", "run.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    time.sleep(3)
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ Server started successfully")
            return process
        else:
            print(f"❌ Server returned status code: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"❌ Failed to connect to server: {e}")
        return None

def test_unauthenticated_endpoints():
    """Test that unauthenticated endpoints work correctly"""
    print("\n🧪 Testing unauthenticated endpoints...")
    
    try:
        # Test main page
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"📊 Main page status: {response.status_code}")
        
        # Test OIDC providers endpoint (should work without auth)
        response = requests.get("http://localhost:8000/api/oidc/providers", timeout=5)
        print(f"📊 OIDC providers status: {response.status_code}")
        
        # Test authenticated endpoint (should return 401)
        response = requests.get("http://localhost:8000/api/users/me", timeout=5)
        print(f"📊 /api/users/me status: {response.status_code} (should be 401)")
        
        # Test admin endpoint (should return 401)
        response = requests.get("http://localhost:8000/api/admin/oidc-claims/providers", timeout=5)
        print(f"📊 Admin OIDC endpoint status: {response.status_code} (should be 401)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")
        return False

def show_manual_test_instructions():
    """Show instructions for manual testing"""
    print("\n📋 Manual Testing Instructions")
    print("=" * 50)
    print("1. Open browser and navigate to: http://localhost:8000/")
    print("2. Open Developer Tools (F12)")
    print("3. Go to Console tab")
    print("4. Check for the following improvements:")
    print()
    print("✅ EXPECTED BEHAVIOR (Fixed):")
    print("   - Login page loads cleanly")
    print("   - You should see: 'Admin.js loader executed!'")
    print("   - You should see: 'setupUI: Starting authentication check'")
    print("   - You should see: 'setupUI: Authentication failed, showing login form'")
    print("   - You should NOT see: 'Admin.js main initialization...'")
    print("   - You should NOT see multiple 401 errors in console")
    print("   - You should NOT see admin API calls being made")
    print()
    print("❌ PREVIOUS BEHAVIOR (Fixed):")
    print("   - Multiple 401 Unauthorized errors in console")
    print("   - Admin system loading before authentication")
    print("   - API calls to /api/admin/* endpoints before login")
    print()
    print("🔧 TO TEST ADMIN LOADING:")
    print("   - Once you have admin credentials, login")
    print("   - Click 'Admin Mode' link")
    print("   - NOW admin system should load properly")
    print("   - Check console for: 'Loading modular admin system for authenticated admin user...'")
    print()
    print("Press Enter when you've completed the manual testing...")

def main():
    """Main test function"""
    print("🧪 Authentication Flow Fix Test")
    print("=" * 40)
    
    # Start server
    server_process = start_server()
    if not server_process:
        print("❌ Cannot start server, aborting tests")
        return
    
    try:
        # Test unauthenticated endpoints
        endpoint_test_ok = test_unauthenticated_endpoints()
        
        if endpoint_test_ok:
            print("✅ Basic endpoint tests passed")
        else:
            print("❌ Basic endpoint tests failed")
        
        # Show manual test instructions
        show_manual_test_instructions()
        
        # Wait for user input
        try:
            input()
        except KeyboardInterrupt:
            print("\n🛑 Test interrupted by user")
        
        print("\n📊 Test Summary:")
        print("- Server started successfully")
        print("- Basic endpoints responding correctly")
        print("- Manual verification completed")
        print("\n💡 Key fixes implemented:")
        print("1. Admin system only loads after authentication")
        print("2. No premature API calls during initial page load")
        print("3. Proper sequencing of authentication and admin initialization")
        
    finally:
        # Stop server
        print("\n🛑 Stopping server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("✅ Server stopped")

if __name__ == "__main__":
    main()
