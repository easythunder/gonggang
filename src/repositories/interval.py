"""Interval repository for CRUD operations on intervals."""
import logging
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session
from src.models.models import Interval, Submission
from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class IntervalRepository(BaseRepository[Interval]):
    """Repository for Interval entity."""

    def __init__(self, session: Session):
        """Initialize with Interval model."""
        super().__init__(session, Interval)

    def create_interval(
        self,
        submission_id: uuid.UUID,
        day_of_week: int,
        start_minute: int,
        end_minute: int,
    ) -> Interval:
        """Create a new interval."""
        interval = self.create(
            submission_id=submission_id,
            day_of_week=day_of_week,
            start_minute=start_minute,
            end_minute=end_minute,
        )
        return interval

    def create_bulk(
        self,
        submission_id: uuid.UUID,
        intervals_data: List[tuple],
    ) -> List[Interval]:
        """Create multiple intervals in bulk.
        
        Args:
            submission_id: UUID of submission
            intervals_data: List of (day_of_week, start_minute, end_minute) tuples
        
        Returns:
            List of created intervals
        """
        intervals = []
        for day_of_week, start_minute, end_minute in intervals_data:
            interval = self.create_interval(
                submission_id=submission_id,
                day_of_week=day_of_week,
                start_minute=start_minute,
                end_minute=end_minute,
            )
            intervals.append(interval)
        return intervals

    def list_by_submission(self, submission_id: uuid.UUID) -> List[Interval]:
        """Get all intervals for a submission."""
        return (
            self.session.query(Interval)
            .filter(Interval.submission_id == submission_id)
            .all()
        )

    def list_by_group(self, group_id: uuid.UUID) -> List[Interval]:
        """Get all intervals for a group (across all submissions)."""
        from src.models.models import Submission
        
        return (
            self.session.query(Interval)
            .join(Submission, Interval.submission_id == Submission.id)
            .filter(Submission.group_id == group_id)
            .all()
        )

    def list_by_day(self, day_of_week: int) -> List[Interval]:
        """Get all intervals for a specific day."""
        return (
            self.session.query(Interval)
            .filter(Interval.day_of_week == day_of_week)
            .all()
        )

    def delete_by_submission_id(self, submission_id: uuid.UUID) -> int:
        """Delete all intervals for a submission.
        
        Returns:
            Number of intervals deleted
        """
        count = (
            self.session.query(Interval)
            .filter(Interval.submission_id == submission_id)
            .delete()
        )
        self.session.flush()
        logger.debug(f"Deleted {count} intervals for submission {submission_id}")
        return count

    def get_count_by_submission(self, submission_id: uuid.UUID) -> int:
        """Get count of intervals for a submission."""
        return (
            self.session.query(Interval)
            .filter(Interval.submission_id == submission_id)
            .count()
        )

    def get_count_by_group(self, group_id: uuid.UUID) -> int:
        """Get total count of intervals for a group."""
        return len(self.list_by_group(group_id))
