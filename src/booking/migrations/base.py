"""
Base migration class for database schema changes.
"""

import hashlib
from abc import ABC, abstractmethod
from typing import Optional
from sqlalchemy.orm import Session


class BaseMigration(ABC):
    """
    Base class for all database migrations.
    
    Each migration must implement the up() method to apply changes.
    Optionally, the down() method can be implemented for rollbacks.
    """
    
    # Migration metadata
    version: str = ""
    description: str = ""
    
    def __init__(self, session: Session):
        self.session = session
    
    @abstractmethod
    def up(self) -> None:
        """
        Apply the migration changes.
        This method must be implemented by all migrations.
        """
        pass
    
    def down(self) -> None:
        """
        Rollback the migration changes.
        This method is optional but recommended for production safety.
        """
        raise NotImplementedError(f"Rollback not implemented for migration {self.version}")
    
    def get_checksum(self) -> str:
        """
        Calculate a checksum of the migration file to detect changes.
        """
        import inspect
        source = inspect.getsource(self.__class__)
        return hashlib.md5(source.encode()).hexdigest()
    
    def validate(self) -> bool:
        """
        Validate migration requirements before execution.
        Override this method to add custom validation logic.
        """
        return True
    
    def get_info(self) -> dict:
        """
        Get migration information for tracking.
        """
        return {
            'version': self.version,
            'description': self.description,
            'checksum': self.get_checksum(),
            'class_name': self.__class__.__name__
        }
    
    def __str__(self) -> str:
        return f"Migration {self.version}: {self.description}"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(version='{self.version}')>"
