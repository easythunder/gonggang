"""FreeTimeResult repository for CRUD operations on calculation results."""
import logging
import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session
from src.models.models import FreeTimeResult, SubmissionStatus
from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class FreeTimeResultRepository(BaseRepository[FreeTimeResult]):
    """Repository for FreeTimeResult entity."""

    def __init__(self, session: Session):
        """Initialize with FreeTimeResult model."""
        super().__init__(session, FreeTimeResult)

    def create_result(
        self,
        group_id: uuid.UUID,
        availability_by_day: Optional[dict] = None,
        free_time_intervals: Optional[dict] = None,
        free_time_intervals_30min: Optional[dict] = None,
        free_time_intervals_60min: Optional[dict] = None,
    ) -> FreeTimeResult:
        """Create a new calculation result with duration-filtered variants.
        
        Args:
            group_id: Group UUID
            availability_by_day: Availability grid
            free_time_intervals: ≥10min free time slots
            free_time_intervals_30min: ≥30min free time slots
            free_time_intervals_60min: ≥60min free time slots
        """
        result = self.create(
            group_id=group_id,
            version=1,
            availability_by_day=availability_by_day,
            free_time_intervals=free_time_intervals,
            free_time_intervals_30min=free_time_intervals_30min,
            free_time_intervals_60min=free_time_intervals_60min,
            computed_at=datetime.utcnow(),
            status=SubmissionStatus.SUCCESS,
        )
        return result

    def find_by_group_id(self, group_id: uuid.UUID) -> Optional[FreeTimeResult]:
        """Find result by group ID (should be unique)."""
        return (
            self.session.query(FreeTimeResult)
            .filter(FreeTimeResult.group_id == group_id)
            .first()
        )

    def update_result(
        self,
        group_id: uuid.UUID,
        availability_by_day: Optional[dict] = None,
        free_time_intervals: Optional[dict] = None,
        free_time_intervals_30min: Optional[dict] = None,
        free_time_intervals_60min: Optional[dict] = None,
    ) -> Optional[FreeTimeResult]:
        """Update calculation result with duration filters, incrementing version.
        
        Args:
            group_id: Group UUID
            availability_by_day: Availability grid
            free_time_intervals: ≥10min slots
            free_time_intervals_30min: ≥30min slots
            free_time_intervals_60min: ≥60min slots
        """
        result = self.find_by_group_id(group_id)
        if not result:
            return None

        # Increment version
        new_version = (result.version or 0) + 1
        
        updated = self.session.query(FreeTimeResult).filter(
            FreeTimeResult.group_id == group_id
        ).update({
            FreeTimeResult.version: new_version,
            FreeTimeResult.availability_by_day: availability_by_day,
            FreeTimeResult.free_time_intervals: free_time_intervals,
            FreeTimeResult.free_time_intervals_30min: free_time_intervals_30min,
            FreeTimeResult.free_time_intervals_60min: free_time_intervals_60min,
            FreeTimeResult.computed_at: datetime.utcnow(),
            FreeTimeResult.status: SubmissionStatus.SUCCESS,
        })
        
        self.session.flush()
        logger.debug(f"Updated FreeTimeResult for group {group_id}, v{new_version}")
        return self.find_by_group_id(group_id)

    def update_status(
        self,
        group_id: uuid.UUID,
        status: SubmissionStatus,
        error_code: Optional[str] = None,
    ) -> Optional[FreeTimeResult]:
        """Update result status (for error states)."""
        return self.update(
            group_id,
            status=status,
            error_code=error_code,
        )

    def get_version(self, group_id: uuid.UUID) -> int:
        """Get current version for a group."""
        result = self.find_by_group_id(group_id)
        return result.version if result else 0

    def delete_by_group_id(self, group_id: uuid.UUID) -> bool:
        """Delete result for a group."""
        result = self.find_by_group_id(group_id)
        if not result:
            return False
        
        return self.delete_instance(result)
