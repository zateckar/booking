#!/usr/bin/env python3
"""
Test script to verify the logs API functionality
"""
import sys
import os
import requests
import json
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_logs_api():
    """Test the logs API endpoints"""
    base_url = "http://localhost:8000"
    
    # First, we need to login to get an admin token
    # For this test, we'll assume there's an admin user
    print("Testing logs API...")
    
    # Test login (you'll need to have an admin user created)
    login_data = {
        "username": "admin@example.com",  # Replace with actual admin email
        "password": "admin123"  # Replace with actual admin password
    }
    
    try:
        # Login
        response = requests.post(f"{base_url}/api/token", data=login_data)
        if response.status_code != 200:
            print(f"Login failed: {response.status_code} - {response.text}")
            print("Please create an admin user first or update the credentials in this test")
            return
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test logs endpoint
        print("Testing logs endpoint...")
        response = requests.get(f"{base_url}/api/admin/logs", headers=headers)
        if response.status_code == 200:
            logs = response.json()
            print(f"Successfully retrieved {len(logs)} logs")
            if logs:
                print(f"Latest log: {logs[0]['timestamp']} [{logs[0]['level']}] {logs[0]['message']}")
        else:
            print(f"Failed to get logs: {response.status_code} - {response.text}")
        
        # Test log stats
        print("Testing log stats endpoint...")
        response = requests.get(f"{base_url}/api/admin/logs/stats", headers=headers)
        if response.status_code == 200:
            stats = response.json()
            print(f"Log stats: {json.dumps(stats, indent=2)}")
        else:
            print(f"Failed to get log stats: {response.status_code} - {response.text}")
        
        # Test log levels
        print("Testing log levels endpoint...")
        response = requests.get(f"{base_url}/api/admin/logs/levels", headers=headers)
        if response.status_code == 200:
            levels = response.json()
            print(f"Available log levels: {levels}")
        else:
            print(f"Failed to get log levels: {response.status_code} - {response.text}")
        
        # Test log loggers
        print("Testing log loggers endpoint...")
        response = requests.get(f"{base_url}/api/admin/logs/loggers", headers=headers)
        if response.status_code == 200:
            loggers = response.json()
            print(f"Available loggers: {loggers}")
        else:
            print(f"Failed to get loggers: {response.status_code} - {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Could not connect to the application. Make sure it's running on http://localhost:8000")
    except Exception as e:
        print(f"Error testing logs API: {e}")

if __name__ == "__main__":
    test_logs_api()