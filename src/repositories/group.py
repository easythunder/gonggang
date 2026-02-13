"""Group repository for CRUD operations on groups."""
import logging
import uuid
from typing import Optional, List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from src.models.models import Group
from src.repositories.base import BaseRepository
from src.config import config

logger = logging.getLogger(__name__)


class GroupRepository(BaseRepository[Group]):
    """Repository for Group entity."""

    def __init__(self, session: Session):
        """Initialize with Group model."""
        super().__init__(session, Group)

    def create_group(self, name: str, display_unit_minutes: int) -> Group:
        """Create a new group with generated tokens and URLs."""
        group_id = uuid.uuid4()
        admin_token = str(uuid.uuid4())
        # Simple URL construction - in production use proper URL builder
        invite_url = f"https://example.com/invite/{group_id}/{admin_token}"
        share_url = f"https://example.com/share/{group_id}"
        
        # expires_at = last_activity_at + 72 hours
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=config.DELETION_RETENTION_HOURS)

        group = self.create(
            id=group_id,
            name=name,
            display_unit_minutes=display_unit_minutes,
            created_at=now,
            last_activity_at=now,
            expires_at=expires_at,
            admin_token=admin_token,
            invite_url=invite_url,
            share_url=share_url,
            max_participants=config.MAX_PARTICIPANTS_PER_GROUP,
        )
        return group

    def find_by_invite_url(self, invite_url: str) -> Optional[Group]:
        """Find group by invite URL."""
        return self.session.query(Group).filter(Group.invite_url == invite_url).first()

    def find_by_share_url(self, share_url: str) -> Optional[Group]:
        """Find group by share URL."""
        return self.session.query(Group).filter(Group.share_url == share_url).first()

    def find_by_id(self, group_id: uuid.UUID) -> Optional[Group]:
        """Find group by ID."""
        return self.session.query(Group).filter(Group.id == group_id).first()

    def find_expired_groups(self, limit: int = 100) -> List[Group]:
        """Find all groups that have expired."""
        now = datetime.utcnow()
        return (
            self.session.query(Group)
            .filter(Group.expires_at <= now)
            .limit(limit)
            .all()
        )

    def update_last_activity(self, group_id: uuid.UUID) -> Optional[Group]:
        """Update last_activity_at for a group (which resets expiration)."""
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=config.DELETION_RETENTION_HOURS)
        
        return self.update(
            group_id,
            last_activity_at=now,
            expires_at=expires_at,
        )

    def check_expiry(self, group_id: uuid.UUID) -> bool:
        """Check if a group is expired."""
        group = self.get_by_id(group_id)
        if not group:
            return True  # Doesn't exist = expired
        return group.is_expired()

    def get_submission_count(self, group_id: uuid.UUID) -> int:
        """Get count of successful submissions for a group."""
        from src.models.models import Submission, SubmissionStatus
        
        return (
            self.session.query(Submission)
            .filter(
                Submission.group_id == group_id,
                Submission.status == SubmissionStatus.SUCCESS,
            )
            .count()
        )
