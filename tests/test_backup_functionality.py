#!/usr/bin/env python3
"""
Test script for Azure Blob Storage backup functionality
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
from datetime import datetime, timezone
from src.booking.backup_service import create_backup_service
from src.booking.database import SessionLocal
from src.booking.models import BackupSettings

def test_backup_service():
    """Test the backup service functionality"""
    
    print("=== Azure Blob Storage Backup Test ===\n")
    
    # Test configuration (replace with your actual values)
    storage_account = "test_storage_account"
    container_name = "test_container"
    sas_token = "test_sas_token"
    
    print("Configuration:")
    print(f"  Storage Account: {storage_account}")
    print(f"  Container Name: {container_name}")
    print(f"  SAS Token: {'*' * 20}...")
    print()
    
    # Create backup service
    backup_service = create_backup_service(storage_account, container_name, sas_token)
    
    # Test 1: Connection test
    print("1. Testing connection to Azure Blob Storage...")
    result = backup_service.test_connection()
    if result['success']:
        print(f"   ✅ Connection successful: {result['message']}")
    else:
        print(f"   ❌ Connection failed: {result['error']}")
    print()
    
    # Test 2: List existing backups
    print("2. Listing existing backups...")
    result = backup_service.list_backups(limit=5)
    if result['success']:
        print(f"   ✅ Found {result['count']} backups:")
        for backup in result['backups'][:3]:  # Show first 3
            print(f"      - {backup}")
        if result['count'] > 3:
            print(f"      ... and {result['count'] - 3} more")
    else:
        print(f"   ❌ Failed to list backups: {result['error']}")
    print()
    
    # Test 3: Backup database (only if database exists)
    db_path = "./booking.db"
    if os.path.exists(db_path):
        print("3. Testing database backup...")
        result = backup_service.upload_database_backup(db_path)
        if result['success']:
            print(f"   ✅ Backup successful:")
            print(f"      - Blob Name: {result['blob_name']}")
            print(f"      - File Size: {result['file_size_mb']} MB")
            print(f"      - Timestamp: {result['timestamp']}")
        else:
            print(f"   ❌ Backup failed: {result['error']}")
    else:
        print("3. Skipping database backup test (no booking.db found)")
    print()

def test_database_settings():
    """Test database settings functionality"""
    
    print("=== Database Settings Test ===\n")
    
    db = SessionLocal()
    try:
        # Check if backup settings table exists
        backup_settings = db.query(BackupSettings).first()
        
        if not backup_settings:
            print("1. Creating initial backup settings...")
            backup_settings = BackupSettings(
                enabled=False,
                storage_account="test_account",
                container_name="test_container",
                sas_token="test_token",
                backup_frequency="daily",
                backup_hour=2,
                keep_backups=30
            )
            db.add(backup_settings)
            db.commit()
            print("   ✅ Initial backup settings created")
        else:
            print("1. Found existing backup settings:")
            print(f"   - Enabled: {backup_settings.enabled}")
            print(f"   - Storage Account: {backup_settings.storage_account}")
            print(f"   - Container: {backup_settings.container_name}")
            print(f"   - Frequency: {backup_settings.backup_frequency}")
            print(f"   - Hour: {backup_settings.backup_hour}")
            print(f"   - Keep Backups: {backup_settings.keep_backups}")
            print(f"   - Last Backup: {backup_settings.last_backup_time}")
            print(f"   - Last Status: {backup_settings.last_backup_status}")
        
        print("   ✅ Database settings test completed")
        
    except Exception as e:
        print(f"   ❌ Database settings test failed: {e}")
    finally:
        db.close()
    print()

async def test_scheduler_integration():
    """Test scheduler integration"""
    
    print("=== Scheduler Integration Test ===\n")
    
    try:
        from src.booking.scheduler import ReportScheduler
        
        print("1. Testing scheduler initialization...")
        scheduler = ReportScheduler()
        print("   ✅ Scheduler initialized successfully")
        
        print("2. Testing backup check method...")
        # Test the backup checking method
        await scheduler._check_and_perform_backups()
        print("   ✅ Backup check method executed (check logs for details)")
        
    except Exception as e:
        print(f"   ❌ Scheduler integration test failed: {e}")
    print()

def print_setup_instructions():
    """Print setup instructions for users"""
    
    print("=== Setup Instructions ===\n")
    
    print("To use Azure Blob Storage backup functionality:")
    print()
    print("1. Create an Azure Storage Account:")
    print("   - Go to Azure Portal")
    print("   - Create a new Storage Account")
    print("   - Note the account name")
    print()
    print("2. Create a container:")
    print("   - In your storage account, create a new container")
    print("   - Name it something like 'database-backups'")
    print("   - Set access level to 'Private'")
    print()
    print("3. Generate SAS token:")
    print("   - Go to Storage Account > Shared access signature")
    print("   - Select services: Blob")
    print("   - Select resource types: Container, Object")
    print("   - Select permissions: Read, Write, List, Create")
    print("   - Set expiration date (e.g., 1 year from now)")
    print("   - Generate SAS token")
    print()
    print("4. Configure in admin panel:")
    print("   - Go to Admin Panel > System tab")
    print("   - Fill in Storage Account, Container Name, and SAS Token")
    print("   - Test connection")
    print("   - Enable automatic backups")
    print("   - Set frequency and schedule")
    print()

def main():
    """Main test function"""
    
    print("Starting Azure Blob Storage Backup Tests\n")
    print("=" * 50)
    print()
    
    # Test database settings
    test_database_settings()
    
    # Test scheduler integration
    asyncio.run(test_scheduler_integration())
    
    # Print setup instructions
    print_setup_instructions()
    
    print("=" * 50)
    print("Testing completed!")
    print()
    print("Note: To test actual backup functionality, you need to:")
    print("1. Run the migration script: python migrate_backup_settings.py")
    print("2. Configure real Azure credentials in the admin panel")
    print("3. Test the connection and perform a backup")

if __name__ == "__main__":
    main()
