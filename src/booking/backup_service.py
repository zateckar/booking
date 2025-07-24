import os
import shutil
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AzureBlobBackupService:
    """Service for backing up SQLite database to Azure Blob Storage using SAS token"""
    
    def __init__(self, storage_account: str, container_name: str, sas_token: str):
        self.storage_account = storage_account
        self.container_name = container_name
        self.sas_token = sas_token
        self.base_url = f"https://{storage_account}.blob.core.windows.net"
    
    def upload_database_backup(self, db_path: str, backup_filename: Optional[str] = None) -> dict:
        """
        Upload SQLite database file to Azure Blob Storage
        
        Args:
            db_path: Path to the SQLite database file
            backup_filename: Optional custom filename for the backup
            
        Returns:
            dict: Result with success status and details
        """
        try:
            if not os.path.exists(db_path):
                raise FileNotFoundError(f"Database file not found: {db_path}")
            
            # Generate backup filename if not provided
            if backup_filename is None:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                backup_filename = f"booking_db_backup_{timestamp}.db"
            
            # Create temporary copy of database to ensure consistency
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
                shutil.copy2(db_path, temp_path)
            
            try:
                # Upload to Azure Blob Storage
                result = self._upload_file_to_blob(temp_path, backup_filename)
                return result
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Database backup failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _upload_file_to_blob(self, file_path: str, blob_name: str) -> dict:
        """
        Upload file to Azure Blob Storage using REST API
        
        Args:
            file_path: Path to the file to upload
            blob_name: Name for the blob in Azure Storage
            
        Returns:
            dict: Upload result
        """
        try:
            # Construct the blob URL
            blob_url = f"{self.base_url}/{self.container_name}/{blob_name}"
            
            # Add SAS token to URL
            if "?" in self.sas_token:
                full_url = f"{blob_url}{self.sas_token}"
            else:
                full_url = f"{blob_url}?{self.sas_token}"
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Prepare HTTP request
            headers = {
                'x-ms-blob-type': 'BlockBlob',
                'Content-Type': 'application/octet-stream',
                'Content-Length': str(len(file_content))
            }
            
            # Create HTTP request
            req = urllib.request.Request(full_url, data=file_content, headers=headers, method='PUT')
            
            # Send request
            with urllib.request.urlopen(req) as response:
                if response.status in [200, 201]:
                    file_size_mb = len(file_content) / (1024 * 1024)
                    logger.info(f"Database backup uploaded successfully: {blob_name} ({file_size_mb:.2f} MB)")
                    return {
                        "success": True,
                        "blob_name": blob_name,
                        "blob_url": blob_url,
                        "file_size_bytes": len(file_content),
                        "file_size_mb": round(file_size_mb, 2),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    raise Exception(f"Upload failed with status: {response.status}")
                    
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP error during upload: {e.code} - {e.reason}"
            if hasattr(e, 'read'):
                try:
                    error_body = e.read().decode('utf-8')
                    error_msg += f" - {error_body}"
                except:
                    pass
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            error_msg = f"Unexpected error during upload: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def test_connection(self) -> dict:
        """
        Test connection to Azure Blob Storage by attempting to list container contents
        
        Returns:
            dict: Test result
        """
        try:
            # Construct the container URL for listing blobs
            list_url = f"{self.base_url}/{self.container_name}?restype=container&comp=list"
            
            # Add SAS token
            if "?" in self.sas_token:
                # SAS token already has parameters
                full_url = f"{list_url}&{self.sas_token.lstrip('?')}"
            else:
                full_url = f"{list_url}&{self.sas_token}"
            
            # Create HTTP request
            req = urllib.request.Request(full_url, method='GET')
            
            # Send request
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    logger.info("Azure Blob Storage connection test successful")
                    return {
                        "success": True,
                        "message": "Connection to Azure Blob Storage successful",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    raise Exception(f"Connection test failed with status: {response.status}")
                    
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP error during connection test: {e.code} - {e.reason}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            error_msg = f"Connection test failed: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def list_backups(self, limit: int = 50) -> dict:
        """
        List existing backup files in Azure Blob Storage
        
        Args:
            limit: Maximum number of backups to return
            
        Returns:
            dict: List of backup files
        """
        try:
            # Construct the container URL for listing blobs
            list_url = f"{self.base_url}/{self.container_name}?restype=container&comp=list&maxresults={limit}"
            
            # Add SAS token
            if "?" in self.sas_token:
                full_url = f"{list_url}&{self.sas_token.lstrip('?')}"
            else:
                full_url = f"{list_url}&{self.sas_token}"
            
            # Create HTTP request
            req = urllib.request.Request(full_url, method='GET')
            
            # Send request
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    response_data = response.read().decode('utf-8')
                    logger.debug(f"Azure Blob list response: {response_data}")
                    
                    # Parse XML response - handle single line XML
                    backups = []
                    
                    # Use regex to find all Name tags since XML might be on one line
                    import re
                    name_pattern = r'<Name>(.*?)</Name>'
                    matches = re.findall(name_pattern, response_data)
                    
                    for blob_name in matches:
                        if blob_name.endswith('.db'):
                            backups.append(blob_name)
                    
                    logger.info(f"Raw backup list found: {backups}")
                    
                    # Sort backups by filename (which contains timestamp) - newest first
                    # Backup filename format: booking_db_backup_YYYYMMDD_HHMMSS.db
                    def extract_timestamp(filename):
                        try:
                            # Extract timestamp from filename
                            import re
                            match = re.search(r'(\d{8}_\d{6})', filename)
                            if match:
                                timestamp_str = match.group(1)
                                # Convert to datetime for proper sorting
                                year = int(timestamp_str[0:4])
                                month = int(timestamp_str[4:6])
                                day = int(timestamp_str[6:8])
                                hour = int(timestamp_str[9:11])
                                minute = int(timestamp_str[11:13])
                                second = int(timestamp_str[13:15]) if len(timestamp_str) > 13 else 0
                                return datetime(year, month, day, hour, minute, second)
                        except:
                            pass
                        # Fallback to filename for sorting
                        return filename
                    
                    # Sort by timestamp (newest first)
                    backups.sort(key=extract_timestamp, reverse=True)
                    
                    # Apply the limit to the sorted results
                    backups = backups[:limit]
                    
                    logger.info(f"Found {len(backups)} backup files (requested limit: {limit})")
                    
                    return {
                        "success": True,
                        "backups": backups,
                        "count": len(backups),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    raise Exception(f"List backups failed with status: {response.status}")
                    
        except Exception as e:
            error_msg = f"Failed to list backups: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


def create_backup_service(storage_account: str, container_name: str, sas_token: str) -> AzureBlobBackupService:
    """Factory function to create backup service instance"""
    return AzureBlobBackupService(storage_account, container_name, sas_token)
