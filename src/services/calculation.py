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
        """Calculate time slots where participants are NOT all together.
        
        Complement logic: find time slots where NOT ALL participants are available.
        This is the inverse of AND intersection - it shows when at least one person is free.
        
        Args:
            submission_intervals: Dict mapping submission_id → interval list
        
        Returns:
            Dict mapping day_of_week → list of (start_minute, end_minute) tuples
            representing times when NOT all participants are scheduled
        """
        if not submission_intervals:
            # 참여자가 없으면 24시간 모두 반환
            return {day: [(0, 1440)] for day in range(7)}

        # 모든 참여자의 시간을 합침 (Union operation)
        # 결과: 최소 1명 이상이 예약한 시간들
        merged_by_day: Dict[int, List[Tuple[int, int]]] = {day: [] for day in range(7)}
        
        # 모든 제출자의 모든 간격을 수집
        submission_list = list(submission_intervals.items())
        if not submission_list:
            return {day: [(0, 1440)] for day in range(7)}

        for submission_id, intervals in submission_list:
            for interval in intervals:
                day = interval.day_of_week
                if day not in merged_by_day:
                    merged_by_day[day] = []
                merged_by_day[day].append((interval.start_minute, interval.end_minute))

        logger.debug(f"Collected intervals from {len(submission_list)} submissions")

        # 각 요일별로 겹치는 슬롯 병합
        for day in range(7):
            if merged_by_day[day]:
                merged_by_day[day] = merge_adjacent_slots(merged_by_day[day])
                logger.debug(f"Day {day}: merged to {len(merged_by_day[day])} slots")

        # 이제 merged_by_day는 모든 참여자의 시간을 합친 것
        # 24시간(0~1440)에서 이 부분을 제외하면 "겹치지 않는 시간" (여집합)
        complement_by_day: Dict[int, List[Tuple[int, int]]] = {day: [] for day in range(7)}
        
        for day in range(7):
            available_slots = merged_by_day[day]
            # 24시간에서 모든 참여자의 시간을 제외
            complement_slots = self._calculate_time_complement(available_slots)
            complement_by_day[day] = complement_slots
            logger.debug(f"Day {day} complement: {len(complement_slots)} free slots")

        return complement_by_day

    def _calculate_time_complement(
        self,
        intervals: List[Tuple[int, int]]
    ) -> List[Tuple[int, int]]:
        """Calculate the complement of intervals in a 24-hour day (0-1440 minutes).
        
        Returns time slots NOT covered by the input intervals.
        Filters to only include slots of minimum 10 minutes duration.
        Example: if intervals=[(540, 660), (900, 1080)], returns [(0, 540), (660, 900), (1080, 1440)]
        
        Args:
            intervals: Sorted, merged list of (start, end) tuples representing occupied times
        
        Returns:
            List of (start_minute, end_minute) tuples representing FREE time slots (≥10 min)
        """
        DAY_START = 0       # 자정 (00:00)
        DAY_END = 1440      # 다음날 자정 (24:00)
        MIN_DURATION = 10   # 최소 10분 이상만 자유시간으로 간주

        if not intervals:
            # 아무 시간도 점유되지 않으면: 24시간 모두 자유
            return [(DAY_START, DAY_END)]

        complement = []
        current_time = DAY_START
        
        # 각 점유 슬롯 사이의 빈 시간 찾기
        for start, end in intervals:
            if current_time < start:
                duration = start - current_time
                # 현재 시간부터 다음 슬롯 시작까지 빈 시간 발견
                if duration >= MIN_DURATION:
                    complement.append((current_time, start))
                    logger.debug(f"Free slot: {current_time}~{start} (duration: {duration}min)")
            
            # 현재 위치 업데이트 (혹시 겹치는 슬롯이 있을 수 있음)
            current_time = max(current_time, end)
        
        # 마지막 점유 슬롯 이후부터 자정까지의 빈 시간
        if current_time < DAY_END:
            duration = DAY_END - current_time
            if duration >= MIN_DURATION:
                complement.append((current_time, DAY_END))
                logger.debug(f"Free slot (evening): {current_time}~{DAY_END} (duration: {duration}min)")
        
        return complement

    def _filter_slots_by_min_duration(
        self,
        free_time_by_day: Dict[int, List[Tuple[int, int]]],
        min_duration_minutes: int
    ) -> Dict[int, List[Tuple[int, int]]]:
        """Filter free-time slots by minimum duration.
        
        Args:
            free_time_by_day: Dict mapping day_of_week → list of (start, end) tuples
            min_duration_minutes: Minimum duration in minutes (10, 30, 60, etc.)
        
        Returns:
            Filtered dict with only slots meeting minimum duration
        """
        filtered = {}
        for day in range(7):
            day_slots = free_time_by_day.get(day, [])
            filtered_slots = [
                (start, end) for start, end in day_slots
                if (end - start) >= min_duration_minutes
            ]
            filtered[day] = filtered_slots
            
            if day_slots and filtered_slots:
                removed = len(day_slots) - len(filtered_slots)
                if removed > 0:
                    logger.debug(f"Day {day}: filtered out {removed} slots (< {min_duration_minutes}min)")
        
        return filtered

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
                availability_by_day={day: [] for day in range(7)},
                free_time_intervals={day: [] for day in range(7)},
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
        """Store calculation result in database with multiple minimum duration filters.
        
        Stores 3 versions:
        - free_time_intervals: default with ≥10min filter
        - free_time_intervals_30min: slots ≥30min
        - free_time_intervals_60min: slots ≥60min
        
        Args:
            group_id: UUID of group
            free_time_by_day: Dict mapping day_of_week → intervals (already filtered to ≥10min)
        
        Returns:
            Stored FreeTimeResult object
        """
        try:
            # 기본 자유시간 (≥10분, 이미 필터링됨)
            free_time_10min = free_time_by_day
            
            # 30분 이상 자유시간 필터링
            free_time_30min = self._filter_slots_by_min_duration(free_time_by_day, 30)
            
            # 60분 이상 자유시간 필터링
            free_time_60min = self._filter_slots_by_min_duration(free_time_by_day, 60)
            
            # 저장소에 데이터 전달
            store_data = {
                "group_id": group_id,
                "availability_by_day": free_time_by_day,
                "free_time_intervals": free_time_10min,
                "free_time_intervals_30min": free_time_30min,
                "free_time_intervals_60min": free_time_60min,
            }
            
            # Get or create result
            existing_result = self.free_time_result_repo.find_by_group_id(group_id)
            
            if existing_result:
                # Update existing result (version auto-increments in repository)
                self.free_time_result_repo.update_result(**store_data)
                logger.info(f"Updated calculation result for group {group_id}")
                logger.debug(
                    f"  10min: {sum(len(v) for v in free_time_10min.values())} slots | "
                    f"30min: {sum(len(v) for v in free_time_30min.values())} slots | "
                    f"60min: {sum(len(v) for v in free_time_60min.values())} slots"
                )
            else:
                # Create new result
                result = self.free_time_result_repo.create_result(**store_data)
                logger.info(f"Created new calculation result v1 for group {group_id}")
                logger.debug(
                    f"  10min: {sum(len(v) for v in free_time_10min.values())} slots | "
                    f"30min: {sum(len(v) for v in free_time_30min.values())} slots | "
                    f"60min: {sum(len(v) for v in free_time_60min.values())} slots"
                )

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
