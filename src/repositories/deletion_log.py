"""DeletionLog repository for CRUD operations on deletion logs."""
import logging
import uuid
from typing import List, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from src.models.models import DeletionLog
from src.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class DeletionLogRepository(BaseRepository[DeletionLog]):
    """Repository for DeletionLog entity."""

    def __init__(self, session: Session):
        """Initialize with DeletionLog model."""
        super().__init__(session, DeletionLog)

    def create_log(
        self,
        group_id: Optional[uuid.UUID],
        reason: str,
        submission_count: Optional[int] = None,
        asset_count: Optional[int] = None,
        error_code: Optional[str] = None,
        retry_count: int = 0,
    ) -> DeletionLog:
        """Create a deletion log entry."""
        log = self.create(
            group_id=group_id,
            deleted_at=datetime.utcnow(),
            reason=reason,
            submission_count=submission_count,
            asset_count=asset_count,
            error_code=error_code,
            retry_count=retry_count,
        )
        return log

    def list_by_group(self, group_id: uuid.UUID) -> List[DeletionLog]:
        """Get deletion log entries for a group."""
        return (
            self.session.query(DeletionLog)
            .filter(DeletionLog.group_id == group_id)
            .order_by(DeletionLog.deleted_at.desc())
            .all()
        )

    def list_by_reason(self, reason: str) -> List[DeletionLog]:
        """Get deletion log entries by reason (e.g., 'expired', 'manual')."""
        return (
            self.session.query(DeletionLog)
            .filter(DeletionLog.reason == reason)
            .order_by(DeletionLog.deleted_at.desc())
            .all()
        )

    def list_recent(self, hours: int = 24) -> List[DeletionLog]:
        """Get recent deletion log entries."""
        since = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.session.query(DeletionLog)
            .filter(DeletionLog.deleted_at >= since)
            .order_by(DeletionLog.deleted_at.desc())
            .all()
        )

    def get_audit_trail(self, group_id: uuid.UUID, limit: int = 100) -> List[DeletionLog]:
        """Get full audit trail for a group."""
        return (
            self.session.query(DeletionLog)
            .filter(DeletionLog.group_id == group_id)
            .order_by(DeletionLog.deleted_at.desc())
            .limit(limit)
            .all()
        )

    def count_failures(self, hours: int = 24) -> int:
        """Count deletion failures in last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.session.query(DeletionLog)
            .filter(
                DeletionLog.deleted_at >= since,
                DeletionLog.error_code != None,  # Has error
            )
            .count()
        )

    def count_by_reason(self, reason: str) -> int:
        """Count log entries by reason."""
        return (
            self.session.query(DeletionLog)
            .filter(DeletionLog.reason == reason)
            .count()
        )
