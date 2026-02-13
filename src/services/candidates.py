"""Candidate time slot extraction and ranking service.

Extracts candidate time slots from free-time intervals.
Ranks by duration, time of day, and overlap count.
"""
import logging
from typing import List, Tuple, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# Minimum duration for candidate slots (in minutes)
DEFAULT_MIN_DURATION = 30


class CandidateSlot:
    """Represents a candidate meeting time."""
    
    def __init__(
        self,
        day_of_week: int,
        start_minute: int,
        end_minute: int,
        overlap_count: int = 0,
        total_participants: int = 0
    ):
        """Initialize candidate slot.
        
        Args:
            day_of_week: 0-6 (Monday-Sunday)
            start_minute: Start time in minutes from midnight
            end_minute: End time in minutes from midnight
            overlap_count: Number of participants available in this slot
            total_participants: Total number of participants
        """
        self.day_of_week = day_of_week
        self.start_minute = start_minute
        self.end_minute = end_minute
        self.overlap_count = overlap_count
        self.total_participants = total_participants
    
    @property
    def duration(self) -> int:
        """Duration in minutes."""
        return self.end_minute - self.start_minute
    
    @property
    def availability_percentage(self) -> float:
        """Percentage of participants available."""
        if self.total_participants == 0:
            return 0.0
        return (self.overlap_count / self.total_participants) * 100
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response."""
        return {
            "day_of_week": self.day_of_week,
            "start_minute": self.start_minute,
            "end_minute": self.end_minute,
            "duration": self.duration,
            "available_participants": self.overlap_count,
            "total_participants": self.total_participants,
            "availability_percentage": round(self.availability_percentage, 1),
        }
    
    def __repr__(self):
        return (
            f"CandidateSlot(day={self.day_of_week}, "
            f"{self.start_minute}-{self.end_minute}, "
            f"{self.overlap_count}/{self.total_participants})"
        )
    
    def __eq__(self, other):
        if not isinstance(other, CandidateSlot):
            return False
        return (
            self.day_of_week == other.day_of_week
            and self.start_minute == other.start_minute
            and self.end_minute == other.end_minute
        )


class CandidateExtractor:
    """Extract candidate time slots from free-time intervals."""
    
    def __init__(self, min_duration: int = DEFAULT_MIN_DURATION):
        """Initialize extractor.
        
        Args:
            min_duration: Minimum duration for candidate slots (minutes)
        """
        self.min_duration = min_duration
        logger.info(f"Initialized CandidateExtractor with min_duration={min_duration}min")
    
    def extract_candidates(
        self,
        free_time_by_day: dict,
        total_participants: int
    ) -> List[CandidateSlot]:
        """Extract candidate slots from free-time intervals.
        
        Args:
            free_time_by_day: Dict mapping day_of_week → interval list
            total_participants: Total number of participants
        
        Returns:
            List of CandidateSlot objects
        """
        try:
            candidates = []
            
            for day in range(7):
                intervals = free_time_by_day.get(day, [])
                
                for interval in intervals:
                    if isinstance(interval, dict):
                        start = interval.get("start_minute", 0)
                        end = interval.get("end_minute", 0)
                    elif isinstance(interval, (list, tuple)):
                        start, end = interval[0], interval[1]
                    else:
                        continue
                    
                    # All participants are free in intersection
                    overlap_count = total_participants
                    
                    # Check minimum duration
                    if end - start < self.min_duration:
                        logger.debug(
                            f"Skipping slot (day {day}, {start}-{end}): "
                            f"duration {end - start}min < {self.min_duration}min"
                        )
                        continue
                    
                    candidate = CandidateSlot(
                        day_of_week=day,
                        start_minute=start,
                        end_minute=end,
                        overlap_count=overlap_count,
                        total_participants=total_participants
                    )
                    candidates.append(candidate)
            
            logger.info(f"Extracted {len(candidates)} candidate slots from {total_participants} participants")
            return candidates

        except Exception as e:
            logger.error(f"Failed to extract candidates: {e}", exc_info=True)
            return []
    
    def rank_candidates(
        self,
        candidates: List[CandidateSlot],
        strategy: str = "duration"
    ) -> List[CandidateSlot]:
        """Rank candidate slots.
        
        Strategies:
        - 'duration': Longest duration first (best for groups looking for long meetings)
        - 'overlap': Most participants available first
        - 'balanced': Duration + availability
        - 'earliest': Earliest in week first
        
        Args:
            candidates: List of candidate slots
            strategy: Ranking strategy
        
        Returns:
            Ranked list of candidates
        """
        if not candidates:
            return []
        
        if strategy == "duration":
            # Sort: longest duration, then earliest time, then day
            ranked = sorted(
                candidates,
                key=lambda c: (-c.duration, c.day_of_week, c.start_minute)
            )
        elif strategy == "overlap":
            # Sort: most overlap, then longest duration
            ranked = sorted(
                candidates,
                key=lambda c: (-c.overlap_count, -c.duration, c.day_of_week, c.start_minute)
            )
        elif strategy == "balanced":
            # Sort: duration * overlap ratio
            ranked = sorted(
                candidates,
                key=lambda c: (
                    -(c.duration * c.availability_percentage),
                    -c.duration,
                    c.day_of_week,
                    c.start_minute
                )
            )
        elif strategy == "earliest":
            # Sort: earliest in week and time
            ranked = sorted(
                candidates,
                key=lambda c: (c.day_of_week, c.start_minute, -c.duration)
            )
        else:
            ranked = candidates
        
        logger.info(f"Ranked {len(ranked)} candidates using '{strategy}' strategy")
        return ranked
    
    def merge_adjacent_slots(
        self,
        candidates: List[CandidateSlot]
    ) -> List[CandidateSlot]:
        """Merge adjacent candidate slots on same day.
        
        Args:
            candidates: List of candidate slots
        
        Returns:
            List with adjacent slots merged
        """
        if not candidates:
            return []
        
        # Group by day
        by_day = {}
        for candidate in candidates:
            day = candidate.day_of_week
            if day not in by_day:
                by_day[day] = []
            by_day[day].append(candidate)
        
        # Sort each day's slots by start time
        merged = []
        for day in range(7):
            day_slots = sorted(
                by_day.get(day, []),
                key=lambda c: c.start_minute
            )
            
            current = None
            for slot in day_slots:
                if current is None:
                    current = slot
                elif current.end_minute == slot.start_minute:
                    # Adjacent: merge
                    current = CandidateSlot(
                        day_of_week=current.day_of_week,
                        start_minute=current.start_minute,
                        end_minute=slot.end_minute,
                        overlap_count=current.overlap_count,
                        total_participants=current.total_participants
                    )
                else:
                    # Gap: save current and start new
                    merged.append(current)
                    current = slot
            
            if current:
                merged.append(current)
        
        # Re-sort all days
        merged = sorted(
            merged,
            key=lambda c: (c.day_of_week, c.start_minute)
        )
        
        logger.info(f"Merged adjacent slots: {len(candidates)} → {len(merged)}")
        return merged
    
    def filter_by_duration(
        self,
        candidates: List[CandidateSlot],
        min_duration: int
    ) -> List[CandidateSlot]:
        """Filter candidates by minimum duration.
        
        Args:
            candidates: List of candidates
            min_duration: Minimum duration in minutes
        
        Returns:
            Filtered list
        """
        filtered = [c for c in candidates if c.duration >= min_duration]
        logger.info(f"Filtered by duration {min_duration}min: {len(candidates)} → {len(filtered)}")
        return filtered
    
    def filter_by_day(
        self,
        candidates: List[CandidateSlot],
        days: List[int]
    ) -> List[CandidateSlot]:
        """Filter candidates to specific days.
        
        Args:
            candidates: List of candidates
            days: List of day_of_week values (0-6)
        
        Returns:
            Filtered list
        """
        filtered = [c for c in candidates if c.day_of_week in days]
        logger.info(f"Filtered by days {days}: {len(candidates)} → {len(filtered)}")
        return filtered
    
    def filter_by_time_window(
        self,
        candidates: List[CandidateSlot],
        start_minute: int,
        end_minute: int
    ) -> List[CandidateSlot]:
        """Filter candidates to specific time window.
        
        Args:
            candidates: List of candidates
            start_minute: Minimum start time
            end_minute: Maximum end time
        
        Returns:
            Filtered list
        """
        filtered = [
            c for c in candidates
            if c.start_minute >= start_minute and c.end_minute <= end_minute
        ]
        logger.info(
            f"Filtered by time window {start_minute}-{end_minute}: "
            f"{len(candidates)} → {len(filtered)}"
        )
        return filtered


def generate_candidate_summary(candidates: List[CandidateSlot]) -> dict:
    """Generate summary statistics for candidates.
    
    Args:
        candidates: List of candidate slots
    
    Returns:
        Summary dict with statistics
    """
    if not candidates:
        return {
            "total_candidates": 0,
            "candidates_by_day": {},
            "longest_slot": None,
            "average_duration": 0,
            "total_available_hours": 0,
        }
    
    # Calculate by day
    by_day = {day: [] for day in range(7)}
    for candidate in candidates:
        by_day[candidate.day_of_week].append(candidate)
    
    candidates_by_day = {
        day: len(slots)
        for day, slots in by_day.items()
        if slots
    }
    
    # Calculate statistics
    total_minutes = sum(c.duration for c in candidates)
    average_duration = int(total_minutes / len(candidates)) if candidates else 0
    longest_slot = max(candidates, key=lambda c: c.duration) if candidates else None
    
    return {
        "total_candidates": len(candidates),
        "candidates_by_day": candidates_by_day,
        "longest_slot": longest_slot.to_dict() if longest_slot else None,
        "average_duration": average_duration,
        "total_available_hours": round(total_minutes / 60, 1),
        "total_available_minutes": total_minutes,
    }
