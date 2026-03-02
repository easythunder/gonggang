"""Submission service for managing schedule submissions."""
import logging
from typing import Tuple, Optional, List, TYPE_CHECKING
from uuid import UUID
from src.models.models import Submission, SubmissionStatus
from src.repositories.submission import SubmissionRepository
from src.repositories.interval import IntervalRepository
from src.repositories.group import GroupRepository
from src.services.interval_extractor import IntervalExtractor, IntervalExtractionError, IntervalData
from src.services.everytime_parser import EverytimeTimetableParser, EverytimeParserError
from src.lib.database import DatabaseManager

if TYPE_CHECKING:
    from src.services.calculation import CalculationService

logger = logging.getLogger(__name__)


class SubmissionError(Exception):
    """Raised when submission operation fails."""
    pass


class DuplicateSubmissionError(SubmissionError):
    """Raised when duplicate submission is detected."""
    pass


class EverytimeSubmissionParseError(SubmissionError):
    """Raised when Everytime link parsing/extraction fails."""
    pass


class SubmissionService:
    """Service for managing schedule submissions."""

    def __init__(
        self,
        session,
        submission_repo: Optional[SubmissionRepository] = None,
        interval_repo: Optional[IntervalRepository] = None,
        group_repo: Optional[GroupRepository] = None,
        interval_extractor: Optional[IntervalExtractor] = None,
        calculation_service: Optional["CalculationService"] = None,
    ):
        """Initialize submission service.
        
        Args:
            session: SQLAlchemy session
            submission_repo: SubmissionRepository instance (created if None)
            interval_repo: IntervalRepository instance (created if None)
            group_repo: GroupRepository instance (created if None)
            interval_extractor: IntervalExtractor instance (created if None)
            calculation_service: CalculationService instance (created if None, lazy-loaded)
        """
        self.session = session
        self.submission_repo = submission_repo or SubmissionRepository(session)
        self.interval_repo = interval_repo or IntervalRepository(session)
        self.group_repo = group_repo or GroupRepository(session)
        self.interval_extractor = interval_extractor or IntervalExtractor()
        self._calculation_service = calculation_service

    @property
    def calculation_service(self) -> "CalculationService":
        """Lazy-load calculation service on first access.
        
        This avoids circular imports and allows tests to inject mocks.
        """
        if self._calculation_service is None:
            from src.services.calculation import CalculationService
            self._calculation_service = CalculationService(self.session)
        return self._calculation_service

    def create_submission(
        self,
        group_id: UUID,
        nickname: str,
        intervals: List[IntervalData],
        ocr_success: bool = True,
        error_reason: Optional[str] = None,
    ) -> Tuple[Submission, Optional[str]]:
        """Create a new submission with intervals.
        
        Args:
            group_id: UUID of the group
            nickname: Participant nickname (unique per group)
            intervals: List of IntervalData objects
            ocr_success: Whether OCR parsing succeeded
            error_reason: Error description if OCR failed
        
        Returns:
            Tuple of (Submission object, error_code)
            error_code is None if successful
        
        Raises:
            DuplicateSubmissionError: If nickname already exists in group
            SubmissionError: If database operation fails
        """
        try:
            # Check for duplicate nickname in group
            existing = self.submission_repo.find_by_group_and_nickname(
                group_id, nickname
            )
            if existing is not None:
                logger.warning(f"Duplicate submission for group {group_id}: {nickname}")
                raise DuplicateSubmissionError(
                    f"Nickname '{nickname}' already submitted for this group"
                )

            # Determine status
            if ocr_success and intervals:
                status = SubmissionStatus.SUCCESS
                error_reason = None
            elif ocr_success and not intervals:
                status = SubmissionStatus.SUCCESS
                error_reason = None
            else:
                status = SubmissionStatus.FAILED
                error_reason = error_reason or "OCR parsing failed"

            # Create submission
            submission = self.submission_repo.create_submission(
                group_id=group_id,
                nickname=nickname,
                status=status,
                error_reason=error_reason,
            )

            logger.info(
                f"Created submission {submission.id} for group {group_id}: "
                f"{nickname} ({status})"
            )

            # Store intervals if successful
            if status == SubmissionStatus.SUCCESS and intervals:
                self._store_intervals(submission.id, intervals)
                logger.info(f"Stored {len(intervals)} intervals for submission {submission.id}")

            self.session.commit()

            # Trigger calculation after successful submission (T050)
            # This ensures free-time results are updated immediately
            if status == SubmissionStatus.SUCCESS:
                try:
                    result, calc_error = self.calculation_service.trigger_calculation(group_id)
                    if calc_error:
                        logger.warning(f"Calculation failed after submission: {calc_error}")
                    else:
                        calc_version = result.version if result else "unknown"
                        logger.info(f"Calculation triggered for group {group_id}, version {calc_version}")
                except Exception as e:
                    logger.error(f"Failed to trigger calculation: {e}", exc_info=True)
                    # Don't fail submission if calculation fails - it can be retried later

            return submission, None

        except DuplicateSubmissionError as e:
            logger.warning(str(e))
            self.session.rollback()
            raise
        except Exception as e:
            logger.error(f"Failed to create submission: {e}", exc_info=True)
            self.session.rollback()
            raise SubmissionError(f"Submission creation failed: {str(e)}") from e

    def create_submission_from_everytime_link(
        self,
        group_id: UUID,
        nickname: str,
        everytime_url: str,
        display_unit_minutes: int,
    ) -> Tuple[Submission, List[IntervalData]]:
        """Create submission by parsing Everytime public timetable link.

        Parses link HTML, extracts intervals, and stores them in DB.
        """
        parser = EverytimeTimetableParser()
        if not parser.validate_everytime_url(everytime_url):
            raise EverytimeSubmissionParseError("Invalid Everytime timetable URL")

        try:
            interval_pairs = parser.parse_from_url(everytime_url)
            extractor = IntervalExtractor(display_unit_minutes=display_unit_minutes)
            intervals = extractor.extract_intervals_from_pairs(interval_pairs)
        except (EverytimeParserError, IntervalExtractionError) as e:
            raise EverytimeSubmissionParseError(str(e)) from e

        submission, _ = self.create_submission(
            group_id=group_id,
            nickname=nickname,
            intervals=intervals,
            ocr_success=True,
            error_reason=None,
        )
        return submission, intervals

    def get_submission(self, submission_id: UUID) -> Optional[Submission]:
        """Retrieve a submission by ID.
        
        Args:
            submission_id: UUID of submission
        
        Returns:
            Submission object or None if not found
        """
        try:
            return self.submission_repo.get_by_id(submission_id)
        except Exception as e:
            logger.error(f"Failed to get submission {submission_id}: {e}", exc_info=True)
            return None

    def get_group_submissions(self, group_id: UUID) -> List[Submission]:
        """Get all submissions for a group.
        
        Args:
            group_id: UUID of group
        
        Returns:
            List of Submission objects
        """
        try:
            return self.submission_repo.list_by_group(group_id)
        except Exception as e:
            logger.error(f"Failed to list submissions for group {group_id}: {e}", exc_info=True)
            return []

    def get_successful_submissions(self, group_id: UUID) -> List[Submission]:
        """Get successful submissions for a group.
        
        Args:
            group_id: UUID of group
        
        Returns:
            List of Submission objects with status SUCCESS
        """
        try:
            return self.submission_repo.list_successful_by_group(group_id)
        except Exception as e:
            logger.error(f"Failed to list successful submissions for {group_id}: {e}", exc_info=True)
            return []

    def get_submission_count(self, group_id: UUID) -> int:
        """Get count of submissions for a group.
        
        Args:
            group_id: UUID of group
        
        Returns:
            Count of submissions
        """
        try:
            return self.submission_repo.get_submission_count(group_id)
        except Exception as e:
            logger.error(f"Failed to count submissions for {group_id}: {e}", exc_info=True)
            return 0

    def get_successful_count(self, group_id: UUID) -> int:
        """Get count of successful submissions for a group.
        
        Args:
            group_id: UUID of group
        
        Returns:
            Count of successful submissions
        """
        try:
            return self.submission_repo.get_successful_count(group_id)
        except Exception as e:
            logger.error(f"Failed to count successful submissions for {group_id}: {e}", exc_info=True)
            return 0

    def get_submission_intervals(self, submission_id: UUID) -> List[dict]:
        """Get all intervals for a submission.
        
        Args:
            submission_id: UUID of submission
        
        Returns:
            List of interval dicts
        """
        try:
            intervals = self.interval_repo.list_by_submission(submission_id)
            return [
                {
                    "day_of_week": interval.day_of_week,
                    "start_minute": interval.start_minute,
                    "end_minute": interval.end_minute,
                }
                for interval in intervals
            ]
        except Exception as e:
            logger.error(f"Failed to get intervals for submission {submission_id}: {e}", exc_info=True)
            return []

    def update_submission_status(
        self,
        submission_id: UUID,
        status: SubmissionStatus,
        error_reason: Optional[str] = None,
    ) -> bool:
        """Update submission status.
        
        Args:
            submission_id: UUID of submission
            status: New status
            error_reason: Error description if status is FAILED
        
        Returns:
            True if successful
        """
        try:
            self.submission_repo.update_status(submission_id, status, error_reason)
            self.session.commit()
            logger.info(f"Updated submission {submission_id} status to {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update submission status: {e}", exc_info=True)
            self.session.rollback()
            return False

    def delete_submission(self, submission_id: UUID) -> bool:
        """Delete a submission and its intervals.
        
        Args:
            submission_id: UUID of submission to delete
        
        Returns:
            True if successful
        """
        try:
            # Delete intervals cascade will handle this automatically
            self.submission_repo.delete(submission_id)
            self.session.commit()
            logger.info(f"Deleted submission {submission_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete submission {submission_id}: {e}", exc_info=True)
            self.session.rollback()
            return False

    def _store_intervals(self, submission_id: UUID, intervals: List[IntervalData]) -> None:
        """Store intervals in database.
        
        Args:
            submission_id: UUID of submission
            intervals: List of IntervalData objects
        """
        try:
            interval_dicts = [
                (
                    interval.day_of_week,
                    interval.start_minute,
                    interval.end_minute,
                )
                for interval in intervals
            ]

            self.interval_repo.create_bulk(submission_id, interval_dicts)
            logger.debug(f"Stored {len(interval_dicts)} intervals for submission {submission_id}")
        except Exception as e:
            logger.error(f"Failed to store intervals: {e}", exc_info=True)
            raise SubmissionError(f"Failed to store intervals: {str(e)}") from e

    def update_group_last_activity(self, group_id: UUID) -> bool:
        """Update group's last_activity_at timestamp.
        
        Called after successful submission to extend group expiration.
        
        Args:
            group_id: UUID of group
        
        Returns:
            True if successful
        """
        try:
            self.group_repo.update_last_activity(group_id)
            self.session.commit()
            logger.info(f"Updated last_activity for group {group_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update group last_activity: {e}", exc_info=True)
            self.session.rollback()
            return False
