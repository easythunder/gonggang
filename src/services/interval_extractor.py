"""Interval extraction service for parsing schedule data into normalized intervals.

Converts OCR/schedule text into Interval objects with conservative slot normalization.
"""
import logging
from typing import List, Tuple, Optional
from src.lib.slot_utils import (
    normalize_busy_interval,
    validate_slot_boundaries,
)

logger = logging.getLogger(__name__)

# Display unit to internal slot minutes mapping
DISPLAY_UNIT_TO_SLOT_MINUTES = {
    10: 10,
    20: 20,
    30: 30,
    60: 60,
}

INTERNAL_SLOT_MINUTES = 5


class IntervalExtractionError(Exception):
    """Raised when interval extraction fails."""
    pass


class IntervalExtractor:
    """Extract normalized intervals from schedule data."""

    def __init__(self, display_unit_minutes: int = 30):
        """Initialize interval extractor.
        
        Args:
            display_unit_minutes: User's display unit (10/20/30/60)
        """
        if display_unit_minutes not in DISPLAY_UNIT_TO_SLOT_MINUTES:
            raise ValueError(f"Invalid display_unit: {display_unit_minutes}")
        
        self.display_unit_minutes = display_unit_minutes
        logger.info(f"Initialized interval extractor with {display_unit_minutes}min display unit")

    def extract_intervals_from_pairs(
        self,
        interval_pairs: List[Tuple[int, int, int]],
    ) -> List["IntervalData"]:
        """Convert (day_of_week, start_minute, end_minute) pairs to normalized intervals.
        
        Args:
            interval_pairs: List of (day_of_week, start_minute, end_minute) tuples
                day_of_week: 0-6 (Monday-Sunday)
                start_minute: 0-1439
                end_minute: 0-1439
        
        Returns:
            List of IntervalData objects with normalized slots
        
        Raises:
            IntervalExtractionError: If normalization fails or produces invalid data
        """
        intervals = []

        for day_of_week, start_minute, end_minute in interval_pairs:
            try:
                # Validate day
                if not isinstance(day_of_week, int) or day_of_week < 0 or day_of_week > 6:
                    logger.warning(f"Invalid day_of_week: {day_of_week}, skipping")
                    continue

                # Validate times
                if not isinstance(start_minute, int) or not isinstance(end_minute, int):
                    logger.warning(f"Invalid time types for {day_of_week}: {type(start_minute)}, {type(end_minute)}")
                    continue

                if start_minute < 0 or start_minute > 1440 or end_minute < 0 or end_minute > 1440:
                    logger.warning(f"Time out of range for day {day_of_week}: {start_minute}-{end_minute}")
                    continue

                if start_minute >= end_minute:
                    logger.debug(f"Skipping zero-duration interval (day {day_of_week}: {start_minute}-{end_minute})")
                    continue

                # Normalize with conservative ceil/floor
                normalized_slots = normalize_busy_interval(
                    start_minute,
                    end_minute,
                    self.display_unit_minutes,
                )

                for slot_start, slot_end in normalized_slots:
                    interval = IntervalData(
                        day_of_week=day_of_week,
                        start_minute=slot_start,
                        end_minute=slot_end,
                    )
                    intervals.append(interval)
                    logger.debug(
                        f"Day {day_of_week}: {slot_start}-{slot_end} "
                        f"(normalized from {start_minute}-{end_minute})"
                    )

            except Exception as e:
                logger.error(
                    f"Failed to process interval (day {day_of_week}, "
                    f"{start_minute}-{end_minute}): {e}",
                    exc_info=True,
                )
                raise IntervalExtractionError(
                    f"Failed to normalize interval: {str(e)}"
                ) from e

        logger.info(f"Extracted {len(intervals)} normalized intervals from {len(interval_pairs)} input pairs")
        return intervals

    def extract_intervals_from_text(self, text: str) -> List["IntervalData"]:
        """Extract intervals from schedule text (OCR output).
        
        Args:
            text: Raw text from OCR or manual input
        
        Returns:
            List of normalized intervals
        
        Raises:
            IntervalExtractionError: If parsing or normalization fails
        """
        try:
            # Import OCR service dynamically to avoid circular imports
            from src.services.ocr import OCRWrapper

            ocr = OCRWrapper()
            interval_pairs = ocr.parse_schedule_text(text)
            return self.extract_intervals_from_pairs(interval_pairs)
        except Exception as e:
            logger.error(f"Failed to extract intervals from text: {e}", exc_info=True)
            raise IntervalExtractionError(f"Text parsing failed: {str(e)}") from e

    def validate_intervals(self, intervals: List["IntervalData"]) -> bool:
        """Validate a list of intervals for correctness.
        
        Args:
            intervals: List of IntervalData objects
        
        Returns:
            True if all intervals are valid
        
        Raises:
            IntervalExtractionError: If any interval is invalid
        """
        for interval in intervals:
            if not isinstance(interval, IntervalData):
                raise IntervalExtractionError(
                    f"Expected IntervalData, got {type(interval)}"
                )

            if interval.day_of_week < 0 or interval.day_of_week > 6:
                raise IntervalExtractionError(
                    f"Invalid day_of_week: {interval.day_of_week}"
                )

            if interval.start_minute < 0 or interval.start_minute > 1440:
                raise IntervalExtractionError(
                    f"Invalid start_minute: {interval.start_minute}"
                )

            if interval.end_minute < 0 or interval.end_minute > 1440:
                raise IntervalExtractionError(
                    f"Invalid end_minute: {interval.end_minute}"
                )

            if interval.start_minute >= interval.end_minute:
                raise IntervalExtractionError(
                    f"Invalid interval: start ({interval.start_minute}) >= end ({interval.end_minute})"
                )

            # Validate alignment
            if not validate_slot_boundaries(
                interval.start_minute,
                interval.end_minute,
                self.display_unit_minutes,
            ):
                raise IntervalExtractionError(
                    f"Interval not aligned to {self.display_unit_minutes}-min slots: "
                    f"{interval.start_minute}-{interval.end_minute}"
                )

        return True


class IntervalData:
    """Data class for extracted interval."""

    def __init__(self, day_of_week: int, start_minute: int, end_minute: int):
        """Initialize interval data.
        
        Args:
            day_of_week: 0-6 (Monday-Sunday)
            start_minute: Start time in minutes from midnight
            end_minute: End time in minutes from midnight
        """
        self.day_of_week = day_of_week
        self.start_minute = start_minute
        self.end_minute = end_minute

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "day_of_week": self.day_of_week,
            "start_minute": self.start_minute,
            "end_minute": self.end_minute,
        }

    def __repr__(self) -> str:
        return (
            f"IntervalData(day={self.day_of_week}, "
            f"{self.start_minute}-{self.end_minute})"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, IntervalData):
            return False
        return (
            self.day_of_week == other.day_of_week
            and self.start_minute == other.start_minute
            and self.end_minute == other.end_minute
        )
