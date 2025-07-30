#!/usr/bin/env python3
"""
Fix OIDC provider registration issue.

This script will force refresh all OIDC provider registrations to fix the issue
where providers were registered with incorrect names that included display names.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from booking.oidc import force_refresh_all_providers
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    print("Fixing OIDC provider registrations...")
    print("This will clear all existing registrations and re-register providers with correct names.")
    
    try:
        force_refresh_all_providers()
        print("✅ Successfully refreshed all OIDC provider registrations!")
        print("The OIDC login issue should now be resolved.")
    except Exception as e:
        print(f"❌ Failed to refresh OIDC providers: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
