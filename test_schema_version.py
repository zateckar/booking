#!/usr/bin/env python3
"""
Test script to demonstrate schema version management.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from booking.migrations.schema_version import SchemaVersionManager, validate_database_compatibility
from booking.migrations.runner import MigrationRunner

def main():
    print("🔬 Schema Version Management Demo")
    print("=" * 50)
    
    # 1. Show application schema requirements
    print("\n1️⃣ Application Schema Requirements:")
    schema_info = SchemaVersionManager.get_schema_info()
    print(f"   Required version: {schema_info['required_version']}")
    print(f"   Minimum version: {schema_info['minimum_version']}")
    print(f"   Maximum version: {schema_info['maximum_version']}")
    print(f"   Description: {schema_info['description']}")
    
    # 2. Check database compatibility
    print("\n2️⃣ Database Compatibility Check:")
    runner = MigrationRunner()
    is_compatible, message, details = runner.check_schema_compatibility()
    
    print(f"   Current database version: {details.get('current_version', 'unknown')}")
    print(f"   Compatible: {'✅ Yes' if is_compatible else '❌ No'}")
    print(f"   Reason: {message}")
    
    # 3. Demonstrate version comparison
    print("\n3️⃣ Version Compatibility Examples:")
    test_versions = ["001", "002", "003"]
    
    for version in test_versions:
        compatible, reason = SchemaVersionManager.is_version_compatible(version)
        status = "✅" if compatible else "❌"
        print(f"   Version {version}: {status} {reason}")
    
    # 4. Show how environment variables can override
    print("\n4️⃣ Environment Variable Override Example:")
    print("   You can override schema requirements with:")
    print("   REQUIRED_SCHEMA_VERSION=003")
    print("   MINIMUM_SCHEMA_VERSION=002")
    print("   MAXIMUM_SCHEMA_VERSION=005")
    
    # Test with environment override
    os.environ["REQUIRED_SCHEMA_VERSION"] = "003"
    overridden_version = SchemaVersionManager.get_required_version()
    print(f"   With REQUIRED_SCHEMA_VERSION=003: {overridden_version}")
    
    # Clean up
    del os.environ["REQUIRED_SCHEMA_VERSION"]
    
    print("\n" + "=" * 50)
    print("✅ Schema version management demo completed!")

if __name__ == "__main__":
    # Set up environment
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "sqlite:///app/data/booking.db"
    
    main()
