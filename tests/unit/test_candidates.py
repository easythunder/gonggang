"""Unit tests for candidate extraction and ranking.

Tests slot merging, minimum duration filtering, and ranking strategies.
"""
import pytest
from typing import List, Tuple


class CandidateSlot:
    """Represents a candidate time slot."""
    
    def __init__(
        self,
        day_of_week: int,
        start_minute: int,
        end_minute: int,
        overlap_count: int = 0
    ):
        """Initialize candidate slot.
        
        Args:
            day_of_week: 0-6 (Monday-Sunday)
            start_minute: Start time in minutes from midnight
            end_minute: End time in minutes from midnight
            overlap_count: Number of participants available in this slot
        """
        self.day_of_week = day_of_week
        self.start_minute = start_minute
        self.end_minute = end_minute
        self.overlap_count = overlap_count
    
    @property
    def duration(self) -> int:
        """Duration in minutes."""
        return self.end_minute - self.start_minute
    
    def __eq__(self, other):
        if not isinstance(other, CandidateSlot):
            return False
        return (
            self.day_of_week == other.day_of_week
            and self.start_minute == other.start_minute
            and self.end_minute == other.end_minute
        )
    
    def __repr__(self):
        return f"Slot(day={self.day_of_week}, {self.start_minute}-{self.end_minute}, duration={self.duration}min)"


class TestMergeConsecutiveSlots:
    """Test merging of consecutive slots on same day."""
    
    def test_merge_adjacent_slots_same_day(self):
        """Test: Merge two adjacent slots on same day."""
        slots = [
            CandidateSlot(0, 9 * 60, 10 * 60),      # Mon 9-10
            CandidateSlot(0, 10 * 60, 11 * 60),     # Mon 10-11 (adjacent)
        ]
        
        merged = merge_consecutive_slots(slots)
        
        assert len(merged) == 1
        assert merged[0] == CandidateSlot(0, 9 * 60, 11 * 60)
        assert merged[0].duration == 120
    
    def test_merge_multiple_consecutive_slots(self):
        """Test: Merge multiple consecutive slots."""
        slots = [
            CandidateSlot(0, 9 * 60, 10 * 60),
            CandidateSlot(0, 10 * 60, 11 * 60),
            CandidateSlot(0, 11 * 60, 12 * 60),
        ]
        
        merged = merge_consecutive_slots(slots)
        
        assert len(merged) == 1
        assert merged[0] == CandidateSlot(0, 9 * 60, 12 * 60)
        assert merged[0].duration == 180
    
    def test_no_merge_gap_between_slots(self):
        """Test: Don't merge slots with gap."""
        slots = [
            CandidateSlot(0, 9 * 60, 10 * 60),
            CandidateSlot(0, 11 * 60, 12 * 60),  # 1-hour gap
        ]
        
        merged = merge_consecutive_slots(slots)
        
        assert len(merged) == 2
        assert merged[0].duration == 60
        assert merged[1].duration == 60
    
    def test_no_merge_different_days(self):
        """Test: Don't merge slots on different days."""
        slots = [
            CandidateSlot(0, 9 * 60, 10 * 60),      # Monday
            CandidateSlot(1, 9 * 60, 10 * 60),      # Tuesday
        ]
        
        merged = merge_consecutive_slots(slots)
        
        assert len(merged) == 2
    
    def test_merge_with_overlap(self):
        """Test: Merge overlapping slots (take union)."""
        slots = [
            CandidateSlot(0, 9 * 60, 11 * 60),
            CandidateSlot(0, 10 * 60, 12 * 60),  # Overlaps
        ]
        
        merged = merge_consecutive_slots(slots)
        
        assert len(merged) == 1
        assert merged[0] == CandidateSlot(0, 9 * 60, 12 * 60)
        assert merged[0].duration == 180


class TestMinDurationFilter:
    """Test filtering by minimum duration."""
    
    def test_filter_below_min_duration(self):
        """Test: Remove slots below minimum duration."""
        slots = [
            CandidateSlot(0, 9 * 60, 9 * 60 + 15),      # 15 min (exclude)
            CandidateSlot(0, 10 * 60, 11 * 60),         # 60 min (include)
            CandidateSlot(0, 14 * 60, 14 * 60 + 20),    # 20 min (exclude)
        ]
        
        filtered = filter_by_min_duration(slots, min_duration=30)
        
        assert len(filtered) == 1
        assert filtered[0].duration == 60
    
    def test_filter_exact_min_duration(self):
        """Test: Include slots at exact minimum duration."""
        slots = [
            CandidateSlot(0, 9 * 60, 9 * 60 + 30),      # Exactly 30 min
            CandidateSlot(0, 10 * 60, 11 * 60),         # 60 min
        ]
        
        filtered = filter_by_min_duration(slots, min_duration=30)
        
        assert len(filtered) == 2
    
    def test_filter_all_removed(self):
        """Test: All slots removed if all below minimum."""
        slots = [
            CandidateSlot(0, 9 * 60, 9 * 60 + 10),
            CandidateSlot(0, 10 * 60, 10 * 60 + 10),
        ]
        
        filtered = filter_by_min_duration(slots, min_duration=30)
        
        assert len(filtered) == 0
    
    def test_filter_none_removed(self):
        """Test: No slots removed if min_duration is low."""
        slots = [
            CandidateSlot(0, 9 * 60, 9 * 60 + 10),
            CandidateSlot(0, 10 * 60, 11 * 60),
        ]
        
        filtered = filter_by_min_duration(slots, min_duration=1)
        
        assert len(filtered) == 2


class TestRankingByDuration:
    """Test ranking candidates by duration (longest first)."""
    
    def test_rank_single_slot(self):
        """Test: Single slot ranking."""
        slots = [
            CandidateSlot(0, 9 * 60, 10 * 60),  # 60 min
        ]
        
        ranked = rank_by_duration(slots)
        
        assert ranked[0].duration == 60
    
    def test_rank_multiple_by_duration(self):
        """Test: Multiple slots ranked by duration (longest first)."""
        slots = [
            CandidateSlot(0, 14 * 60, 14 * 60 + 30),    # 30 min
            CandidateSlot(0, 9 * 60, 11 * 60),          # 120 min
            CandidateSlot(0, 13 * 60, 14 * 60),         # 60 min
        ]
        
        ranked = rank_by_duration(slots)
        
        assert ranked[0].duration == 120
        assert ranked[1].duration == 60
        assert ranked[2].duration == 30
    
    def test_rank_equal_duration_by_time(self):
        """Test: Equal duration slots ranked by start time."""
        slots = [
            CandidateSlot(0, 14 * 60, 15 * 60),         # 60 min, starts 2 PM
            CandidateSlot(0, 9 * 60, 10 * 60),          # 60 min, starts 9 AM
            CandidateSlot(0, 12 * 60, 13 * 60),         # 60 min, starts 12 PM
        ]
        
        ranked = rank_by_duration(slots)
        
        # Equal duration: prefer earlier in day
        assert ranked[0].start_minute == 9 * 60
        assert ranked[1].start_minute == 12 * 60
        assert ranked[2].start_minute == 14 * 60
    
    def test_rank_equal_duration_and_time_by_day(self):
        """Test: Equal duration and time ranked by day of week."""
        slots = [
            CandidateSlot(2, 9 * 60, 10 * 60),          # Wed, 60 min, 9 AM
            CandidateSlot(0, 9 * 60, 10 * 60),          # Mon, 60 min, 9 AM
            CandidateSlot(4, 9 * 60, 10 * 60),          # Fri, 60 min, 9 AM
        ]
        
        ranked = rank_by_duration(slots)
        
        # Equal duration/time: prefer earlier in week
        assert ranked[0].day_of_week == 0  # Monday
        assert ranked[1].day_of_week == 2  # Wednesday
        assert ranked[2].day_of_week == 4  # Friday


class TestRankingByOverlap:
    """Test ranking by overlap count (most participants available first)."""
    
    def test_rank_by_overlap_count(self):
        """Test: Rank by number of available participants."""
        slots = [
            CandidateSlot(0, 9 * 60, 10 * 60, overlap_count=2),    # 2 people free
            CandidateSlot(0, 10 * 60, 11 * 60, overlap_count=4),   # 4 people free
            CandidateSlot(0, 11 * 60, 12 * 60, overlap_count=3),   # 3 people free
        ]
        
        ranked = rank_by_overlap(slots)
        
        assert ranked[0].overlap_count == 4
        assert ranked[1].overlap_count == 3
        assert ranked[2].overlap_count == 2
    
    def test_rank_overlap_ties_by_duration(self):
        """Test: Tied overlap counts, then sort by duration."""
        slots = [
            CandidateSlot(0, 9 * 60, 9 * 60 + 30, overlap_count=3),   # 30 min, 3 people
            CandidateSlot(0, 10 * 60, 11 * 60, overlap_count=3),      # 60 min, 3 people
        ]
        
        ranked = rank_by_overlap(slots)
        
        assert ranked[0].overlap_count == 3
        assert ranked[0].duration == 60  # Longer duration preferred when overlap tied
        assert ranked[1].duration == 30


class TestCombinedRanking:
    """Test combined ranking strategy: duration > time > day > overlap."""
    
    def test_combined_ranking(self):
        """Test: Combined ranking with all factors."""
        slots = [
            CandidateSlot(0, 9 * 60, 9 * 60 + 30, overlap_count=2),    # 30 min, Mon, 9am, 2 people
            CandidateSlot(0, 10 * 60, 12 * 60, overlap_count=3),       # 120 min, Mon, 10am, 3 people
            CandidateSlot(2, 9 * 60, 11 * 60, overlap_count=4),        # 120 min, Wed, 9am, 4 people
            CandidateSlot(0, 12 * 60, 13 * 60, overlap_count=5),       # 60 min, Mon, 12pm, 5 people
        ]
        
        ranked = rank_combined(slots, priority="duration")
        
        # Priority: duration (longest first)
        assert ranked[0].duration == 120
        assert ranked[1].duration == 120
        # Among 120-min slots: Mon 10am vs Wed 9am
        # Mon 10am comes first (earlier in week)
        assert ranked[0].day_of_week == 0  # Mon
        assert ranked[1].day_of_week == 2  # Wed


# Helper functions for ranking/filtering

def merge_consecutive_slots(slots: List[CandidateSlot]) -> List[CandidateSlot]:
    """Merge consecutive slots (same day, adjacent or overlapping)."""
    if not slots:
        return []
    
    # Sort by day, then start time
    sorted_slots = sorted(slots, key=lambda s: (s.day_of_week, s.start_minute))
    
    merged = []
    current = sorted_slots[0]
    
    for slot in sorted_slots[1:]:
        # Same day and adjacent/overlapping
        if slot.day_of_week == current.day_of_week and slot.start_minute <= current.end_minute:
            # Merge: extend end time if needed
            current = CandidateSlot(
                current.day_of_week,
                current.start_minute,
                max(current.end_minute, slot.end_minute),
                max(current.overlap_count, slot.overlap_count)
            )
        else:
            merged.append(current)
            current = slot
    
    merged.append(current)
    return merged


def filter_by_min_duration(slots: List[CandidateSlot], min_duration: int) -> List[CandidateSlot]:
    """Filter slots by minimum duration in minutes."""
    return [slot for slot in slots if slot.duration >= min_duration]


def rank_by_duration(slots: List[CandidateSlot]) -> List[CandidateSlot]:
    """Rank slots by duration (longest first), then by time/day."""
    return sorted(
        slots,
        key=lambda s: (-s.duration, s.day_of_week, s.start_minute)
    )


def rank_by_overlap(slots: List[CandidateSlot]) -> List[CandidateSlot]:
    """Rank slots by overlap count (most participants first), then by duration."""
    return sorted(
        slots,
        key=lambda s: (-s.overlap_count, -s.duration, s.day_of_week, s.start_minute)
    )


def rank_combined(
    slots: List[CandidateSlot],
    priority: str = "duration"
) -> List[CandidateSlot]:
    """Rank slots with combined strategy.
    
    Args:
        slots: List of candidate slots
        priority: 'duration', 'overlap', or 'balanced'
    """
    if priority == "duration":
        return rank_by_duration(slots)
    elif priority == "overlap":
        return rank_by_overlap(slots)
    else:  # balanced
        # Priority: duration, then overlap, then time
        return sorted(
            slots,
            key=lambda s: (-s.duration, -s.overlap_count, s.day_of_week, s.start_minute)
        )
