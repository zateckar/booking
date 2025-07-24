#!/usr/bin/env python3
"""Quick script to check OIDC providers in the database"""

import sys
sys.path.append('src')

from booking.database import get_db
from booking import models

def main():
    db = next(get_db())
    providers = db.query(models.OIDCProvider).all()
    
    print(f"Found {len(providers)} OIDC providers:")
    for provider in providers:
        print(f"  ID: {provider.id}")
        print(f"  Issuer: '{provider.issuer}'")
        print(f"  Client ID: {provider.client_id}")
        print(f"  Well-known URL: {provider.well_known_url}")
        print("  ---")

if __name__ == "__main__":
    main()