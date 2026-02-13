"""Group service for handling group-related business logic."""
import logging
import uuid
from typing import Optional, Tuple
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.models.models import Group
from src.repositories.group import GroupRepository
from src.repositories.submission import SubmissionRepository
from src.repositories.interval import IntervalRepository
from src.repositories.free_time_result import FreeTimeResultRepository
from src.lib.nickname import generate_nickname
from src.lib.utils import ErrorCodes
from src.config import config

logger = logging.getLogger(__name__)


class GroupService:
    """Service for group operations."""

    def __init__(self, session: Session):
        """Initialize with database session."""
        self.session = session
        self.group_repo = GroupRepository(session)
        self.submission_repo = SubmissionRepository(session)
        self.interval_repo = IntervalRepository(session)
        self.free_time_repo = FreeTimeResultRepository(session)

    def create_group(
        self,
        group_name: Optional[str] = None,
        display_unit_minutes: int = 30,
    ) -> Tuple[Optional[Group], Optional[str]]:
        """Create a new group.
        
        Args:
            group_name: Optional group name, auto-generated if not provided
            display_unit_minutes: Display granularity (10, 20, 30, 60)
        
        Returns:
            Tuple of (Group, error_code) - only one should be non-None
        """
        # Validate display unit
        if display_unit_minutes not in config.DISPLAY_UNIT_OPTIONS:
            logger.warning(
                f"Invalid display unit: {display_unit_minutes}",
                extra={"field": "display_unit_minutes"}
            )
            return None, ErrorCodes.INVALID_DISPLAY_UNIT

        # Generate group name if not provided
        if not group_name:
            group_name = generate_nickname()
            # Ensure uniqueness by appending suffix if needed
            original_name = group_name
            counter = 1
            while self._group_name_exists(group_name):
                group_name = f"{original_name}_{counter}"
                counter += 1
                if counter > 100:
                    logger.error("Failed to generate unique group name after 100 attempts")
                    return None, ErrorCodes.INTERNAL_ERROR

        # Create group with generated tokens and URLs
        try:
            group = self.group_repo.create_group(group_name, display_unit_minutes)
            self.session.commit()
            logger.info(
                f"Created group: {group.name}",
                extra={
                    "group_id": str(group.id),
                    "display_unit": display_unit_minutes,
                }
            )
            return group, None
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating group: {e}", exc_info=True)
            return None, ErrorCodes.DATABASE_ERROR

    def get_group(self, group_id: uuid.UUID) -> Tuple[Optional[Group], Optional[str]]:
        """Get group by ID with expiration check.
        
        Returns:
            Tuple of (Group, error_code)
        """
        group = self.group_repo.find_by_id(group_id)
        if not group:
            return None, ErrorCodes.GROUP_NOT_FOUND

        # Check expiration
        if group.is_expired():
            logger.info(f"Group expired: {group_id}")
            return None, ErrorCodes.GROUP_EXPIRED

        return group, None

    def get_group_by_invite_url(self, invite_url: str) -> Tuple[Optional[Group], Optional[str]]:
        """Get group by invite URL."""
        group = self.group_repo.find_by_invite_url(invite_url)
        if not group:
            return None, ErrorCodes.GROUP_NOT_FOUND

        if group.is_expired():
            logger.warning(f"Group expired via invite URL: {group.id}")
            return None, ErrorCodes.GROUP_EXPIRED

        return group, None

    def get_group_by_share_url(self, share_url: str) -> Tuple[Optional[Group], Optional[str]]:
        """Get group by share URL."""
        group = self.group_repo.find_by_share_url(share_url)
        if not group:
            return None, ErrorCodes.GROUP_NOT_FOUND

        if group.is_expired():
            logger.warning(f"Group expired via share URL: {group.id}")
            return None, ErrorCodes.GROUP_EXPIRED

        return group, None

    def check_expiry(self, group_id: uuid.UUID) -> bool:
        """Check if group is expired."""
        return self.group_repo.check_expiry(group_id)

    def update_last_activity(self, group_id: uuid.UUID) -> Optional[Group]:
        """Update last_activity_at for a group (resets 72h timer).
        
        Called after successful submission or API request.
        """
        group = self.group_repo.update_last_activity(group_id)
        if group:
            self.session.commit()
            logger.debug(
                f"Updated last activity for group: {group_id}",
                extra={"new_expires_at": group.expires_at.isoformat()}
            )
        return group

    def get_group_stats(self, group_id: uuid.UUID) -> Optional[dict]:
        """Get group statistics (submission count, etc)."""
        group = self.group_repo.find_by_id(group_id)
        if not group:
            return None

        submission_count = self.submission_repo.get_submission_count(group_id)
        successful_count = self.submission_repo.get_successful_count(group_id)
        interval_count = self.interval_repo.get_count_by_group(group_id)

        return {
            "group_id": str(group.id),
            "name": group.name,
            "total_submissions": submission_count,
            "successful_submissions": successful_count,
            "total_intervals": interval_count,
            "display_unit_minutes": group.display_unit_minutes,
            "created_at": group.created_at.isoformat(),
            "last_activity_at": group.last_activity_at.isoformat(),
            "expires_at": group.expires_at.isoformat(),
            "time_remaining_hours": max(
                0,
                (group.expires_at - datetime.utcnow()).total_seconds() / 3600
            ),
        }

    def _group_name_exists(self, name: str) -> bool:
        """Check if group name already exists."""
        group = self.session.query(Group).filter(Group.name == name).first()
        return group is not None
