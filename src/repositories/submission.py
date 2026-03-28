"""Submission repository for CRUD operations on submissions."""
import logging
import uuid
from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session
from src.models.models import Submission, SubmissionStatus
from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class SubmissionRepository(BaseRepository[Submission]):
    """Repository for Submission entity."""

    def __init__(self, session: Session):
        """Initialize with Submission model."""
        super().__init__(session, Submission)

    def create_submission(
        self,
        group_id: uuid.UUID,
        nickname: str,
        status: SubmissionStatus = SubmissionStatus.PENDING,
        error_reason: Optional[str] = None,
    ) -> Submission:
        """Create a new submission."""
        submission = self.create(
            group_id=group_id,
            nickname=nickname,
            submitted_at=datetime.utcnow(),
            status=status,
            error_reason=error_reason,
        )
        return submission

    def find_by_id(self, submission_id: uuid.UUID) -> Optional[Submission]:
        """Find submission by ID."""
        return self.session.query(Submission).filter(Submission.id == submission_id).first()

    def find_by_group_and_nickname(
        self,
        group_id: uuid.UUID,
        nickname: str,
    ) -> Optional[Submission]:
        """Find submission by group and nickname (check for duplicates)."""
        return (
            self.session.query(Submission)
            .filter(
                Submission.group_id == group_id,
                Submission.nickname == nickname,
            )
            .first()
        )

    def list_by_group(self, group_id: uuid.UUID, status: Optional[SubmissionStatus] = None) -> List[Submission]:
        """List submissions for a group, optionally filtered by status."""
        query = self.session.query(Submission).filter(Submission.group_id == group_id)
        
        if status:
            query = query.filter(Submission.status == status)
        
        return query.all()

    def list_successful_by_group(self, group_id: uuid.UUID) -> List[Submission]:
        """List successful submissions for a group."""
        return self.list_by_group(group_id, status=SubmissionStatus.SUCCESS)

    def update_status(
        self,
        submission_id: uuid.UUID,
        status: SubmissionStatus,
        error_reason: Optional[str] = None,
    ) -> Optional[Submission]:
        """Update submission status."""
        return self.update(
            submission_id,
            status=status,
            error_reason=error_reason,
        )

    def delete_by_id(self, submission_id: uuid.UUID) -> bool:
        """Delete submission by ID."""
        return self.delete(submission_id)

    def get_submission_count(self, group_id: uuid.UUID) -> int:
        """Get count of submissions for a group."""
        return self.session.query(Submission).filter(Submission.group_id == group_id).count()

    def get_successful_count(self, group_id: uuid.UUID) -> int:
        """Get count of successful submissions for a group."""
        return (
            self.session.query(Submission)
            .filter(
                Submission.group_id == group_id,
                Submission.status == SubmissionStatus.SUCCESS,
            )
            .count()
        )
