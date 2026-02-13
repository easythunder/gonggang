"""Free-time calculation service using AND logic.

Calculates intersection of all participant intervals (AND operation).
Generates availability grid and candidate time slots.
"""
import logging
from typing import List, Tuple, Optional, Dict
from uuid import UUID
from datetime import datetime as dt
from sqlalchemy.orm import Session

from src.models.models import Group, Submission, Interval, FreeTimeResult, SubmissionStatus
from src.repositories.submission import SubmissionRepository
from src.repositories.interval import IntervalRepository
from src.repositories.free_time_result import FreeTimeResultRepository
from src.lib.slot_utils import get_conflicting_slots, merge_adjacent_slots

logger = logging.getLogger(__name__)


class CalculationError(Exception):
    """Raised when calculation fails."""
    pass


class CalculationService:
    """Service for free-time AND calculations."""

    def __init__(
        self,
        session: Session,
        submission_repo: Optional[SubmissionRepository] = None,
        interval_repo: Optional[IntervalRepository] = None,
        free_time_result_repo: Optional[FreeTimeResultRepository] = None,
    ):
        """Initialize calculation service.
        
        Args:
            session: SQLAlchemy session
            submission_repo: SubmissionRepository instance
            interval_repo: IntervalRepository instance
            free_time_result_repo: FreeTimeResultRepository instance
        """
        self.session = session
        self.submission_repo = submission_repo or SubmissionRepository(session)
        self.interval_repo = interval_repo or IntervalRepository(session)
        self.free_time_result_repo = free_time_result_repo or FreeTimeResultRepository(session)

    def trigger_calculation(self, group_id: UUID) -> Tuple[Optional[FreeTimeResult], Optional[str]]:
        """Trigger calculation for a group.
        
        Called after successful submission to recalculate free time.
        Implements AND logic: result = intersection of all participant intervals.
        
        Args:
            group_id: UUID of group to calculate
        
        Returns:
            Tuple of (FreeTimeResult object, error_code)
            error_code is None if successful
        """
        try:
            logger.info(f"Starting calculation for group {group_id}")

            # Get all successful submissions for group
            submissions = self.submission_repo.list_successful_by_group(group_id)
            
            if not submissions:
                logger.warning(f"No successful submissions for group {group_id}, returning empty result")
                return self._create_empty_result(group_id)

            logger.info(f"Found {len(submissions)} successful submissions")

            # Get intervals for each submission
            submission_intervals: Dict[UUID, List[Interval]] = {}
            for submission in submissions:
                intervals = self.interval_repo.list_by_submission(submission.id)
                submission_intervals[submission.id] = intervals
                logger.debug(f"Submission {submission.nickname}: {len(intervals)} intervals")

            # Calculate AND intersection
            free_time_by_day = self._calculate_and_intersection(submission_intervals)
            
            logger.info(f"AND calculation complete: {sum(len(v) for v in free_time_by_day.values())} total slots")

            # Store result
            result = self._store_calculation_result(group_id, free_time_by_day)
            
            return result, None

        except Exception as e:
            logger.error(f"Calculation failed for group {group_id}: {e}", exc_info=True)
            return None, "CALCULATION_ERROR"

    def recalculate_on_submission(self, group_id: UUID) -> bool:
        """Recalculate after new submission (wrapper for trigger_calculation).
        
        Args:
            group_id: UUID of group
        
        Returns:
            True if successful
        """
        try:
            result, error_code = self.trigger_calculation(group_id)
            return error_code is None
        except Exception as e:
            logger.error(f"Recalculation failed: {e}", exc_info=True)
            return False

    def recalculate_on_deletion(self, group_id: UUID) -> bool:
        """Recalculate after submission deletion.
        
        Called by deletion service after removing a submission.
        
        Args:
            group_id: UUID of group
        
        Returns:
            True if successful
        """
        return self.recalculate_on_submission(group_id)

    def get_calculation_result(self, group_id: UUID) -> Optional[FreeTimeResult]:
        """Get latest calculation result for a group.
        
        Args:
            group_id: UUID of group
        
        Returns:
            FreeTimeResult object or None
        """
        try:
            return self.free_time_result_repo.find_by_group_id(group_id)
        except Exception as e:
            logger.error(f"Failed to get calculation result: {e}", exc_info=True)
            return None

    def _calculate_and_intersection(
        self,
        submission_intervals: Dict[UUID, List[Interval]]
    ) -> Dict[int, List[Tuple[int, int]]]:
        """Calculate AND intersection of all submission intervals.
        
        AND logic: time slot is free iff ALL participants are free.
        
        Args:
            submission_intervals: Dict mapping submission_id → interval list
        
        Returns:
            Dict mapping day_of_week → list of (start_minute, end_minute) tuples
        """
        if not submission_intervals:
            return {day: [] for day in range(7)}

        # Initialize result as all possible intervals by day
        # Then intersect with each participant's intervals
        result_by_day: Dict[int, List[Tuple[int, int]]] = {day: [] for day in range(7)}
        
        submission_list = list(submission_intervals.items())
        if not submission_list:
            return result_by_day

        # Start with first submission's intervals
        first_submission_id, first_intervals = submission_list[0]
        for interval in first_intervals:
            day = interval.day_of_week
            if day not in result_by_day:
                result_by_day[day] = []
            result_by_day[day].append((interval.start_minute, interval.end_minute))

        logger.debug(f"Initialized with {len(first_intervals)} intervals from first submission")

        # Intersect with remaining submissions
        for submission_id, intervals in submission_list[1:]:
            new_result: Dict[int, List[Tuple[int, int]]] = {day: [] for day in range(7)}
            
            # Build intervals dict by day for this submission
            submission_by_day: Dict[int, List[Tuple[int, int]]] = {day: [] for day in range(7)}
            for interval in intervals:
                day = interval.day_of_week
                submission_by_day[day].append((interval.start_minute, interval.end_minute))

            # Intersect on each day
            for day in range(7):
                current_day_intervals = result_by_day.get(day, [])
                submission_day_intervals = submission_by_day.get(day, [])
                
                # Calculate AND for this day
                intersected = self._and_intervals(current_day_intervals, submission_day_intervals)
                new_result[day] = intersected

            result_by_day = new_result
            logger.debug(f"After submission intersection: {sum(len(v) for v in result_by_day.values())} slots remaining")

        return result_by_day

    def _and_intervals(
        self,
        intervals_a: List[Tuple[int, int]],
        intervals_b: List[Tuple[int, int]]
    ) -> List[Tuple[int, int]]:
        """Calculate AND (intersection) of two interval lists on same day.
        
        Args:
            intervals_a: First interval list
            intervals_b: Second interval list
        
        Returns:
            Intersected intervals (sorted, merged)
        """
        if not intervals_a or not intervals_b:
            return []

        result = []
        
        for a_start, a_end in intervals_a:
            for b_start, b_end in intervals_b:
                # Find overlap
                overlap_start = max(a_start, b_start)
                overlap_end = min(a_end, b_end)
                
                if overlap_start < overlap_end:
                    result.append((overlap_start, overlap_end))

        # Merge adjacent/overlapping intervals
        if result:
            result = merge_adjacent_slots(result)

        return result

    def _create_empty_result(self, group_id: UUID) -> Tuple[FreeTimeResult, Optional[str]]:
        """Create empty calculation result (no free time).
        
        Args:
            group_id: UUID of group
        
        Returns:
            Tuple of (empty FreeTimeResult, None)
        """
        try:
            result = self.free_time_result_repo.create_result(
                group_id=group_id,
                version=1,
                availability_by_day={day: [] for day in range(7)},
                free_time_intervals={day: [] for day in range(7)},
                computed_at=dt.utcnow(),
                status="SUCCESS",
                error_code=None
            )
            self.session.commit()
            return result, None
        except Exception as e:
            logger.error(f"Failed to create empty result: {e}", exc_info=True)
            self.session.rollback()
            return None, "STORAGE_ERROR"

    def _store_calculation_result(
        self,
        group_id: UUID,
        free_time_by_day: Dict[int, List[Tuple[int, int]]]
    ) -> FreeTimeResult:
        """Store calculation result in database.
        
        Args:
            group_id: UUID of group
            free_time_by_day: Dict mapping day_of_week → intervals
        
        Returns:
            Stored FreeTimeResult object
        """
        try:
            # Get or create result
            existing_result = self.free_time_result_repo.find_by_group_id(group_id)
            
            if existing_result:
                # Update existing result
                new_version = existing_result.version + 1
                self.free_time_result_repo.update_result(
                    existing_result.id,
                    version=new_version,
                    availability_by_day=free_time_by_day,
                    free_time_intervals=free_time_by_day,
                    computed_at=dt.utcnow(),
                    status="SUCCESS",
                    error_code=None
                )
                logger.info(f"Updated calculation result v{new_version} for group {group_id}")
            else:
                # Create new result
                result = self.free_time_result_repo.create_result(
                    group_id=group_id,
                    version=1,
                    availability_by_day=free_time_by_day,
                    free_time_intervals=free_time_by_day,
                    computed_at=dt.utcnow(),
                    status="SUCCESS",
                    error_code=None
                )
                logger.info(f"Created new calculation result v1 for group {group_id}")

            self.session.commit()
            return self.free_time_result_repo.find_by_group_id(group_id)

        except Exception as e:
            logger.error(f"Failed to store calculation result: {e}", exc_info=True)
            self.session.rollback()
            raise CalculationError(f"Failed to store result: {str(e)}") from e

    def get_calculation_version(self, group_id: UUID) -> int:
        """Get current calculation version for a group.
        
        Args:
            group_id: UUID of group
        
        Returns:
            Version number (0 if no calculation)
        """
        try:
            result = self.free_time_result_repo.find_by_group_id(group_id)
            return result.version if result else 0
        except Exception as e:
            logger.error(f"Failed to get calculation version: {e}", exc_info=True)
            return 0

    def calculate_statistics(self, group_id: UUID) -> dict:
        """Calculate statistics about available time.
        
        Args:
            group_id: UUID of group
        
        Returns:
            Stats dict with total_free_minutes, available_days, etc.
        """
        try:
            result = self.free_time_result_repo.find_by_group_id(group_id)
            
            if not result:
                return {
                    "total_free_minutes": 0,
                    "available_days": 0,
                    "slots_available": 0,
                }

            total_free_minutes = 0
            available_days = 0
            total_slots = 0

            for day in range(7):
                day_intervals = result.free_time_intervals.get(day, [])
                if isinstance(day_intervals, list):
                    for interval in day_intervals:
                        if isinstance(interval, dict):
                            start = interval.get("start_minute", 0)
                            end = interval.get("end_minute", 0)
                            total_free_minutes += max(0, end - start)
                        elif isinstance(interval, (list, tuple)) and len(interval) >= 2:
                            total_free_minutes += max(0, interval[1] - interval[0])
                
                if day_intervals:
                    available_days += 1
                    total_slots += len(day_intervals)

            return {
                "total_free_minutes": total_free_minutes,
                "available_days": available_days,
                "slots_available": total_slots,
                "total_hours": round(total_free_minutes / 60, 1),
            }

        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}", exc_info=True)
            return {}
