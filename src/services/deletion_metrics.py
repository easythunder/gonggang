"""
Deletion monitoring and metrics (T073)

Tracks deletion success rate and other metrics.
"""
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.deletion_log import DeletionLog

logger = logging.getLogger(__name__)


class DeletionMetrics:
    """Tracks deletion metrics for monitoring."""
    
    @staticmethod
    def get_deletion_stats(db: Session, hours: int = 24) -> Dict[str, Any]:
        """
        Get deletion statistics for the past N hours.
        
        Args:
            db: Database session
            hours: Time window in hours (default: 24)
        
        Returns:
            Dict with metrics:
            - total_deleted: Total groups deleted
            - successful_deletions: Count of successful deletions
            - failed_deletions: Count of failed/retried deletions
            - success_rate: Percentage of successful deletions
            - avg_submissions_per_group: Average submissions per deleted group
            - avg_retry_count: Average retry attempts
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Get deletion logs from past N hours
        logs = db.query(DeletionLog).filter(
            DeletionLog.deleted_at >= cutoff_time
        ).all()
        
        if not logs:
            return {
                "total_deleted": 0,
                "successful_deletions": 0,
                "failed_deletions": 0,
                "success_rate": 0.0,
                "avg_submissions_per_group": 0,
                "avg_retry_count": 0,
                "time_window_hours": hours
            }
        
        # Calculate stats
        total = len(logs)
        successful = len([l for l in logs if l.error_code is None])
        failed = total - successful
        success_rate = (successful / total * 100) if total > 0 else 0
        
        avg_submissions = (
            sum(l.submission_count for l in logs) / total
            if total > 0 else 0
        )
        
        avg_retries = (
            sum(l.retry_count for l in logs) / total
            if total > 0 else 0
        )
        
        return {
            "total_deleted": total,
            "successful_deletions": successful,
            "failed_deletions": failed,
            "success_rate": round(success_rate, 2),
            "avg_submissions_per_group": round(avg_submissions, 2),
            "avg_retry_count": round(avg_retries, 2),
            "time_window_hours": hours,
            "period_start": cutoff_time.isoformat() + "Z",
            "period_end": datetime.utcnow().isoformat() + "Z"
        }
    
    @staticmethod
    def log_batch_run(
        db: Session,
        stats: Dict[str, int],
        run_duration_seconds: float
    ) -> None:
        """
        Log batch deletion run statistics.
        
        Args:
            db: Database session
            stats: Stats from BatchDeletionService.run_batch_deletion()
            run_duration_seconds: How long the batch run took
        """
        success_rate = (
            stats.get("deleted", 0) / stats.get("scanned", 1) * 100
            if stats.get("scanned", 0) > 0 else 0
        )
        
        logger.info(
            f"Batch deletion run completed: "
            f"scanned={stats.get('scanned', 0)} "
            f"deleted={stats.get('deleted', 0)} "
            f"failed={stats.get('failed', 0)} "
            f"retried={stats.get('retried', 0)} "
            f"success_rate={success_rate:.1f}% "
            f"duration={run_duration_seconds:.2f}s"
        )
    
    @staticmethod
    def get_failure_alerts(db: Session) -> Dict[str, Any]:
        """
        Get information about deletion failures requiring attention.
        
        Args:
            db: Database session
        
        Returns:
            Dict with failure information:
            - high_failure_rate: If success rate < 80%
            - recent_failures: Recent deletion failures
            - groups_with_alerts: Groups that triggered alerts
        """
        # Get recent stats (last 24 hours)
        stats = DeletionMetrics.get_deletion_stats(db, hours=24)
        
        high_failure = stats["success_rate"] < 80
        
        # Get recent failures
        recent_failed = db.query(DeletionLog).filter(
            DeletionLog.error_code.isnot(None),
            DeletionLog.deleted_at >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(DeletionLog.deleted_at.desc()).limit(10).all()
        
        alerts = {
            "success_rate": stats["success_rate"],
            "high_failure_rate": high_failure,
            "recent_failures_count": len(recent_failed),
            "recent_failures": [
                {
                    "group_id": str(f.group_id),
                    "deleted_at": f.deleted_at.isoformat() + "Z",
                    "error_code": f.error_code,
                    "retry_count": f.retry_count
                }
                for f in recent_failed
            ]
        }
        
        return alerts
