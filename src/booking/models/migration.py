"""
Database models for migration tracking.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from .base import Base


class SchemaMigration(Base):
    """
    Track applied database migrations.
    
    This table stores information about each migration that has been
    applied to the database, including version, checksum, and status.
    """
    __tablename__ = "schema_migrations"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=False)
    checksum = Column(String(32), nullable=False)  # MD5 hash
    class_name = Column(String(100), nullable=False)
    
    # Execution tracking
    applied_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    execution_time_ms = Column(Integer, nullable=True)  # Execution time in milliseconds
    status = Column(String(20), default="applied", nullable=False)  # applied, failed, rolled_back
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<SchemaMigration(version='{self.version}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'version': self.version,
            'description': self.description,
            'checksum': self.checksum,
            'class_name': self.class_name,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'execution_time_ms': self.execution_time_ms,
            'status': self.status,
            'error_message': self.error_message
        }
