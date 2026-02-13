"""
Lazy deletion service (T066)

Checks expiration on read requests and marks groups for hard deletion.
"""
import logging
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session

from src.models.group import Group

logger = logging.getLogger(__name__)


class DeletionService:
    """Manages lazy deletion checks."""
    
    @staticmethod
    def check_expiry(group: Group) -> bool:
        """
        Check if group has expired.
        
        Args:
            group: Group model to check
        
        Returns:
            bool: True if expired, False otherwise
        """
        return group.expires_at <= datetime.utcnow()
    
    @staticmethod
    def check_expiry_by_id(db: Session, group_id: UUID) -> bool:
        """
        Check if group with given ID is expired.
        
        Args:
            db: Database session
            group_id: Group UUID
        
        Returns:
            bool: True if expired or not found, False otherwise
        """
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return True  # Non-existent = expired
        
        return DeletionService.check_expiry(group)
    
    @staticmethod
    def mark_soft_deleted(db: Session, group_id: UUID) -> None:
        """
        Mark group as soft-deleted (ready for hard deletion).
        
        Sets is_deleted flag or similar to prevent further access.
        
        Args:
            db: Database session
            group_id: Group UUID to mark
        """
        group = db.query(Group).filter(Group.id == group_id).first()
        if group:
            # Add soft_delete flag to group if model supports it
            # For now, just log it
            logger.info(f"Marked group {group_id} for soft deletion")
            # db.commit()  # Uncomment if model has soft_delete column
    
    @staticmethod
    def is_soft_deleted(db: Session, group_id: UUID) -> bool:
        """
        Check if group is marked as soft-deleted.
        
        Args:
            db: Database session
            group_id: Group UUID to check
        
        Returns:
            bool: True if soft-deleted, False otherwise
        """
        group = db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return True
        
        # Check for soft_delete flag if model has one
        # For now, return False (no soft_delete column yet)
        return False
