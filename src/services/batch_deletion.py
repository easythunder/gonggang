"""
Batch deletion service (T068-T070)

Implements batch group deletion with:
- Cascade deletion (Group → Submission → Interval → Result)
- Exponential retry logic (1min, 5min, 15min, then 15min)
- Deletion log recording
"""
import logging
from datetime import datetime, timedelta
from uuid import UUID
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session

from src.models.models import Group, Submission, Interval, FreeTimeResult
from src.models.deletion_log import DeletionLog
from src.models.deletion_retry import DeletionRetry

logger = logging.getLogger(__name__)


class BatchDeletionService:
    """Manages batch deletion of expired groups."""
    
    # Retry backoff intervals (in minutes)
    BACKOFF_INTERVALS = {
        1: 1,    # 1st failure: retry in 1 minute
        2: 5,    # 2nd failure: retry in 5 minutes
        3: 15,   # 3rd failure: retry in 15 minutes
    }
    MAX_BACKOFF = 15  # Cap at 15 minutes
    MAX_FAILURES = 3  # Alert after 3 failures
    
    @staticmethod
    def scan_expired_groups(db: Session, current_time: datetime = None) -> List[Group]:
        """
        Scan database for expired groups.
        
        Args:
            db: Database session
            current_time: Current time for comparison (defaults to now)
        
        Returns:
            List of expired Group objects
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        expired = db.query(Group).filter(
            Group.expires_at <= current_time
        ).all()
        
        logger.info(f"Scanned and found {len(expired)} expired groups")
        return expired
    
    @staticmethod
    def hard_delete_group(
        db: Session,
        group_id: UUID,
        reason: str = "expired"
    ) -> int:
        """
        Hard delete group with cascade to submissions, intervals, results.
        
        Args:
            db: Database session
            group_id: Group UUID to delete
            reason: Reason for deletion ('expired', 'manual', etc.)
        
        Returns:
            int: Number of records deleted (or -1 on error)
        """
        try:
            # Get group
            group = db.query(Group).filter(Group.id == group_id).first()
            if not group:
                logger.warning(f"Attempted to delete non-existent group {group_id}")
                return 0
            
            # Count related records for logging
            submissions = db.query(Submission).filter(
                Submission.group_id == group_id
            ).all()
            submission_count = len(submissions)
            
            intervals = db.query(Interval).filter(
                Interval.submission_id.in_([s.id for s in submissions])
            ).all() if submissions else []
            interval_count = len(intervals)
            
            # Delete cascade: Results
            result_count = db.query(FreeTimeResult).filter(
                FreeTimeResult.group_id == group_id
            ).delete()
            
            # Delete cascade: Intervals
            if intervals:
                interval_delete_count = db.query(Interval).filter(
                    Interval.id.in_([i.id for i in intervals])
                ).delete()
            else:
                interval_delete_count = 0
            
            # Delete cascade: Submissions
            submission_delete_count = db.query(Submission).filter(
                Submission.group_id == group_id
            ).delete()
            
            # Delete: Group
            group_delete_count = db.query(Group).filter(
                Group.id == group_id
            ).delete()
            
            # Create deletion log
            log = DeletionLog(
                group_id=group_id,
                deleted_at=datetime.utcnow(),
                reason=reason,
                submission_count=submission_count,
                interval_count=interval_count,
                asset_count=interval_count  # Intervals are main assets
            )
            db.add(log)
            
            # Clean up any retry records
            db.query(DeletionRetry).filter(
                DeletionRetry.group_id == group_id
            ).delete()
            
            db.commit()
            
            total_deleted = (
                group_delete_count +
                submission_delete_count +
                interval_delete_count +
                result_count
            )
            
            logger.info(
                f"Successfully deleted group {group_id}: "
                f"{group_delete_count} groups, "
                f"{submission_delete_count} submissions, "
                f"{interval_delete_count} intervals, "
                f"{result_count} results"
            )
            
            return total_deleted
        
        except Exception as e:
            logger.error(f"Error deleting group {group_id}: {e}")
            db.rollback()
            return -1
    
    @staticmethod
    def run_batch_deletion(
        db: Session,
        current_time: datetime = None,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Run batch deletion cycle.
        
        Scans for expired groups and deletes them with retry handling.
        
        Args:
            db: Database session
            current_time: Current time (defaults to now)
            dry_run: If True, only scan without deleting
        
        Returns:
            Dict with stats: {scanned, deleted, failed, retried}
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        stats = {
            "scanned": 0,
            "deleted": 0,
            "failed": 0,
            "retried": 0,
            "alerted": 0
        }
        
        # Step 1: Scan expired groups
        expired_groups = BatchDeletionService.scan_expired_groups(db, current_time)
        stats["scanned"] = len(expired_groups)
        
        # Step 2: Delete each group with retry handling
        for group in expired_groups:
            result = BatchDeletionService.hard_delete_group(db, group.id)
            
            if result > 0:
                stats["deleted"] += 1
            else:
                # Record retry attempt
                BatchDeletionService.record_retry_attempt(
                    db,
                    group.id,
                    error=f"Deletion failed with result {result}",
                    failure_count=1
                )
                stats["failed"] += 1
                
                # Check if should alert
                if BatchDeletionService.should_alert(3):  # 3 failures
                    stats["alerted"] += 1
                    logger.warning(f"Deletion alert for group {group.id}: max retries exceeded")
        
        # Step 3: Process retries for failed groups
        retries = BatchDeletionService.get_retries_ready_for_attempt(db, current_time)
        for retry in retries:
            result = BatchDeletionService.hard_delete_group(db, retry.group_id)
            
            if result > 0:
                stats["deleted"] += 1
                stats["retried"] += 1
            else:
                # Update retry record
                retry.failure_count += 1
                retry.last_failed_at = current_time
                retry.next_retry_at = BatchDeletionService.calculate_next_retry(
                    retry.failure_count,
                    current_time
                )
                db.add(retry)
                db.commit()
                
                stats["failed"] += 1
                
                if BatchDeletionService.should_alert(retry.failure_count):
                    stats["alerted"] += 1
                    logger.warning(
                        f"Deletion retry alert for group {retry.group_id}: "
                        f"{retry.failure_count} failures"
                    )
        
        logger.info(f"Batch deletion cycle complete: {stats}")
        return stats
    
    @staticmethod
    def record_retry_attempt(
        db: Session,
        group_id: UUID,
        error: str,
        failure_count: int
    ) -> DeletionRetry:
        """
        Record a failed deletion attempt for retry.
        
        Args:
            db: Database session
            group_id: Group UUID
            error: Error message
            failure_count: Current failure count
        
        Returns:
            DeletionRetry record
        """
        retry = db.query(DeletionRetry).filter(
            DeletionRetry.group_id == group_id
        ).first()
        
        if not retry:
            next_retry = BatchDeletionService.calculate_next_retry(
                failure_count,
                datetime.utcnow()
            )
            retry = DeletionRetry(
                group_id=group_id,
                failure_count=failure_count,
                last_failed_at=datetime.utcnow(),
                last_error=error,
                next_retry_at=next_retry
            )
        else:
            retry.failure_count = failure_count
            retry.last_failed_at = datetime.utcnow()
            retry.last_error = error
            retry.next_retry_at = BatchDeletionService.calculate_next_retry(
                failure_count,
                datetime.utcnow()
            )
        
        db.add(retry)
        db.commit()
        
        logger.info(f"Recorded retry attempt for group {group_id}: attempt {failure_count}")
        return retry
    
    @staticmethod
    def calculate_next_retry(
        failure_count: int,
        last_failed_at: datetime
    ) -> datetime:
        """
        Calculate next retry time with exponential backoff.
        
        Args:
            failure_count: Number of failures so far
            last_failed_at: Timestamp of last failure
        
        Returns:
            datetime: When to retry next
        """
        # Determine backoff interval
        backoff_minutes = BatchDeletionService.BACKOFF_INTERVALS.get(
            failure_count,
            BatchDeletionService.MAX_BACKOFF
        )
        
        return last_failed_at + timedelta(minutes=backoff_minutes)
    
    @staticmethod
    def is_retry_ready(
        failure_count: int,
        last_failed_at: datetime,
        current_time: datetime = None
    ) -> bool:
        """
        Check if a failed group is ready for retry attempt.
        
        Args:
            failure_count: Number of failures
            last_failed_at: When it last failed
            current_time: Current time (defaults to now)
        
        Returns:
            bool: True if ready to retry
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        next_retry = BatchDeletionService.calculate_next_retry(failure_count, last_failed_at)
        return current_time >= next_retry
    
    @staticmethod
    def should_alert(failure_count: int) -> bool:
        """
        Check if failure count exceeds alert threshold.
        
        Args:
            failure_count: Number of failures
        
        Returns:
            bool: True if should alert
        """
        return failure_count >= BatchDeletionService.MAX_FAILURES
    
    @staticmethod
    def get_retries_ready_for_attempt(
        db: Session,
        current_time: datetime = None
    ) -> List[DeletionRetry]:
        """
        Get all retry records that are ready for deletion attempt.
        
        Args:
            db: Database session
            current_time: Current time (defaults to now)
        
        Returns:
            List of DeletionRetry records ready to attempt
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        ready = db.query(DeletionRetry).filter(
            DeletionRetry.next_retry_at <= current_time,
            DeletionRetry.failure_count < BatchDeletionService.MAX_FAILURES
        ).all()
        
        return ready
