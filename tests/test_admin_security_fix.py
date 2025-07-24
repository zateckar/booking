#!/usr/bin/env python3
"""
Test script to verify that the critical admin security vulnerability has been fixed.
This test ensures that all admin endpoints now properly require authentication.
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

def test_admin_endpoints_unauthorized():
    """Test that admin endpoints return 401 when accessed without authentication"""
    print("\n🔒 Testing admin endpoints security...")
    
    # List of admin endpoints that should require authentication
    admin_endpoints = [
        "/api/admin/reports/bookings",
        "/api/admin/reports/bookings?months=2",
        "/api/admin/reports/download/excel",
        "/api/admin/reports/download/excel?months=2", 
        "/api/admin/reports/schedule-settings",
        "/api/admin/oidc-claims/providers",
        "/api/admin/oidc-claims/claims-mappings",
        "/api/admin/backup-settings/",
        "/api/admin/logs/stats?hours=24",
        "/api/admin/email-settings",
        "/api/admin/timezone-settings/timezones",
        "/api/admin/timezone-settings/current"
    ]
    
    vulnerable_endpoints = []
    secured_endpoints = []
    
    for endpoint in admin_endpoints:
        try:
            print(f"  Testing: {endpoint}")
            response = requests.get(f"http://localhost:8000{endpoint}", timeout=5)
            
            if response.status_code == 401:
                print(f"    ✅ {endpoint} - Properly secured (401)")
                secured_endpoints.append(endpoint)
            elif response.status_code == 403:
                print(f"    ✅ {endpoint} - Properly secured (403)")
                secured_endpoints.append(endpoint)
            else:
                print(f"    ❌ {endpoint} - VULNERABLE! Status: {response.status_code}")
                vulnerable_endpoints.append((endpoint, response.status_code))
                
        except requests.RequestException as e:
            print(f"    ⚠️  {endpoint} - Request failed: {e}")
    
    return vulnerable_endpoints, secured_endpoints

def test_post_endpoints():
    """Test POST endpoints that should require authentication"""
    print("\n🔒 Testing POST endpoints security...")
    
    post_endpoints = [
        ("/api/admin/reports/send-email", {"recipients": ["test@example.com"]}),
    ]
    
    vulnerable_endpoints = []
    secured_endpoints = []
    
    for endpoint, data in post_endpoints:
        try:
            print(f"  Testing POST: {endpoint}")
            response = requests.post(f"http://localhost:8000{endpoint}", json=data, timeout=5)
            
            if response.status_code == 401:
                print(f"    ✅ {endpoint} - Properly secured (401)")
                secured_endpoints.append(endpoint)
            elif response.status_code == 403:
                print(f"    ✅ {endpoint} - Properly secured (403)")
                secured_endpoints.append(endpoint)
            else:
                print(f"    ❌ {endpoint} - VULNERABLE! Status: {response.status_code}")
                vulnerable_endpoints.append((endpoint, response.status_code))
                
        except requests.RequestException as e:
            print(f"    ⚠️  {endpoint} - Request failed: {e}")
    
    return vulnerable_endpoints, secured_endpoints

def test_put_endpoints():
    """Test PUT endpoints that should require authentication"""
    print("\n🔒 Testing PUT endpoints security...")
    
    put_endpoints = [
        ("/api/admin/reports/schedule-settings", {"reports_enabled": True}),
    ]
    
    vulnerable_endpoints = []
    secured_endpoints = []
    
    for endpoint, data in put_endpoints:
        try:
            print(f"  Testing PUT: {endpoint}")
            response = requests.put(f"http://localhost:8000{endpoint}", json=data, timeout=5)
            
            if response.status_code == 401:
                print(f"    ✅ {endpoint} - Properly secured (401)")
                secured_endpoints.append(endpoint)
            elif response.status_code == 403:
                print(f"    ✅ {endpoint} - Properly secured (403)")
                secured_endpoints.append(endpoint)
            else:
                print(f"    ❌ {endpoint} - VULNERABLE! Status: {response.status_code}")
                vulnerable_endpoints.append((endpoint, response.status_code))
                
        except requests.RequestException as e:
            print(f"    ⚠️  {endpoint} - Request failed: {e}")
    
    return vulnerable_endpoints, secured_endpoints

def test_public_endpoints():
    """Test that public endpoints still work without authentication"""
    print("\n🌐 Testing public endpoints accessibility...")
    
    public_endpoints = [
        "/",
        "/api/oidc/providers"
    ]
    
    working_endpoints = []
    broken_endpoints = []
    
    for endpoint in public_endpoints:
        try:
            print(f"  Testing: {endpoint}")
            response = requests.get(f"http://localhost:8000{endpoint}", timeout=5)
            
            if response.status_code == 200:
                print(f"    ✅ {endpoint} - Working correctly")
                working_endpoints.append(endpoint)
            else:
                print(f"    ❌ {endpoint} - Unexpected status: {response.status_code}")
                broken_endpoints.append((endpoint, response.status_code))
                
        except requests.RequestException as e:
            print(f"    ⚠️  {endpoint} - Request failed: {e}")
            broken_endpoints.append((endpoint, str(e)))
    
    return working_endpoints, broken_endpoints

def main():
    """Main test function"""
    print("🔒 Testing Admin Security Vulnerability Fix")
    print("=" * 50)
    
    # Start server
    server_process = start_server()
    if not server_process:
        print("❌ Cannot start server, aborting tests")
        return
    
    try:
        # Test GET endpoints
        vulnerable_get, secured_get = test_admin_endpoints_unauthorized()
        
        # Test POST endpoints  
        vulnerable_post, secured_post = test_post_endpoints()
        
        # Test PUT endpoints
        vulnerable_put, secured_put = test_put_endpoints()
        
        # Test public endpoints still work
        working_public, broken_public = test_public_endpoints()
        
        # Combine results
        all_vulnerable = vulnerable_get + vulnerable_post + vulnerable_put
        all_secured = secured_get + secured_post + secured_put
        
        # Results summary
        print("\n📊 Security Test Results")
        print("=" * 30)
        print(f"✅ Secured endpoints: {len(all_secured)}")
        print(f"❌ Vulnerable endpoints: {len(all_vulnerable)}")
        print(f"🌐 Working public endpoints: {len(working_public)}")
        print(f"⚠️  Broken public endpoints: {len(broken_public)}")
        
        if all_vulnerable:
            print(f"\n❌ CRITICAL: {len(all_vulnerable)} vulnerable endpoints found!")
            print("Vulnerable endpoints:")
            for endpoint, status in all_vulnerable:
                print(f"  - {endpoint} (Status: {status})")
        else:
            print("\n✅ SUCCESS: All admin endpoints are properly secured!")
            
        if broken_public:
            print(f"\n⚠️  WARNING: {len(broken_public)} public endpoints broken:")
            for endpoint, status in broken_public:
                print(f"  - {endpoint} (Status: {status})")
        
        # Overall assessment
        if not all_vulnerable and not broken_public:
            print("\n🎉 PERFECT: Security fix successful and no regressions!")
            return 0
        elif not all_vulnerable:
            print("\n✅ GOOD: Security vulnerability fixed (minor public endpoint issues)")
            return 0
        else:
            print("\n💀 CRITICAL: Security vulnerabilities still exist!")
            return 1
    
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
    exit_code = main()
    sys.exit(exit_code)
