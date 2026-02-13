"""Unit tests for AND calculation logic (free-time intersection).

Tests the core logic: result = AND(all participant intervals)
Conservative logic: only time slots where ALL participants are free.
"""
import pytest
from typing import List, Tuple, Set


class IntervalSet:
    """Helper class for interval set operations."""
    
    def __init__(self, intervals: List[Tuple[int, int]] = None):
        """Initialize with list of (start, end) minute pairs."""
        self.intervals = sorted(intervals or [])
    
    def and_with(self, other: "IntervalSet") -> "IntervalSet":
        """Calculate intersection (AND) of two interval sets."""
        result = []
        
        for s1, e1 in self.intervals:
            for s2, e2 in other.intervals:
                # Find overlap
                overlap_start = max(s1, s2)
                overlap_end = min(e1, e2)
                
                if overlap_start < overlap_end:
                    result.append((overlap_start, overlap_end))
        
        # Merge adjacent intervals
        merged = []
        for start, end in sorted(result):
            if merged and merged[-1][1] == start:
                merged[-1] = (merged[-1][0], end)
            else:
                merged.append((start, end))
        
        return IntervalSet(merged)
    
    def total_duration(self) -> int:
        """Calculate total duration in minutes."""
        return sum(end - start for start, end in self.intervals)
    
    def __eq__(self, other):
        if isinstance(other, IntervalSet):
            return self.intervals == other.intervals
        return False
    
    def __repr__(self):
        return f"IntervalSet({self.intervals})"


class TestTwoPersonAnd:
    """Test AND logic for 2 participants."""
    
    def test_two_person_complete_overlap(self):
        """Test: Both participants have exact same schedule."""
        person_a = IntervalSet([(9 * 60, 10 * 60), (14 * 60, 15 * 60)])  # 9-10, 14-15
        person_b = IntervalSet([(9 * 60, 10 * 60), (14 * 60, 15 * 60)])  # 9-10, 14-15
        
        result = person_a.and_with(person_b)
        
        assert result == IntervalSet([(9 * 60, 10 * 60), (14 * 60, 15 * 60)])
        assert result.total_duration() == 120  # 2 hours
    
    def test_two_person_partial_overlap(self):
        """Test: Participants have partial schedule overlap."""
        person_a = IntervalSet([(9 * 60, 11 * 60)])  # 9-11
        person_b = IntervalSet([(10 * 60, 12 * 60)])  # 10-12
        
        result = person_a.and_with(person_b)
        
        assert result == IntervalSet([(10 * 60, 11 * 60)])
        assert result.total_duration() == 60  # 1 hour
    
    def test_two_person_no_overlap(self):
        """Test: Participants have no overlapping schedule."""
        person_a = IntervalSet([(9 * 60, 10 * 60)])  # 9-10
        person_b = IntervalSet([(14 * 60, 15 * 60)])  # 14-15
        
        result = person_a.and_with(person_b)
        
        assert result == IntervalSet([])
        assert result.total_duration() == 0
    
    def test_two_person_one_empty(self):
        """Test: One participant has no free time."""
        person_a = IntervalSet([(9 * 60, 10 * 60)])
        person_b = IntervalSet([])  # No free time
        
        result = person_a.and_with(person_b)
        
        assert result == IntervalSet([])
        assert result.total_duration() == 0
    
    def test_two_person_multiple_non_adjacent_intervals(self):
        """Test: Multiple non-adjacent intervals with partial overlap."""
        person_a = IntervalSet([
            (9 * 60, 10 * 60),      # 9-10
            (12 * 60, 14 * 60),     # 12-14
            (16 * 60, 18 * 60)      # 16-18
        ])
        person_b = IntervalSet([
            (8 * 60, 10.5 * 60),    # 8-10:30
            (13 * 60, 17 * 60)      # 13-17
        ])
        
        result = person_a.and_with(person_b)
        
        assert result == IntervalSet([
            (9 * 60, 10 * 60),      # 9-10 (overlap of [9-10] and [8-10:30])
            (13 * 60, 14 * 60),     # 13-14 (overlap of [12-14] and [13-17])
            (16 * 60, 17 * 60)      # 16-17 (overlap of [16-18] and [13-17])
        ])
        assert result.total_duration() == 180  # 3 hours


class TestThreePersonAnd:
    """Test AND logic for 3+ participants."""
    
    def test_three_person_all_overlap(self):
        """Test: All 3 participants have overlapping schedule."""
        person_a = IntervalSet([(9 * 60, 12 * 60)])
        person_b = IntervalSet([(10 * 60, 13 * 60)])
        person_c = IntervalSet([(11 * 60, 14 * 60)])
        
        # A AND B
        result = person_a.and_with(person_b)
        # (A AND B) AND C
        result = result.and_with(person_c)
        
        assert result == IntervalSet([(11 * 60, 12 * 60)])
        assert result.total_duration() == 60  # 1 hour
    
    def test_three_person_middle_person_blocks(self):
        """Test: Middle person has no overlap with one side."""
        person_a = IntervalSet([(9 * 60, 11 * 60)])
        person_b = IntervalSet([(14 * 60, 16 * 60)])  # No overlap with A
        person_c = IntervalSet([(10 * 60, 15 * 60)])
        
        result = person_a.and_with(person_b)
        result = result.and_with(person_c)
        
        assert result == IntervalSet([])  # No common time
        assert result.total_duration() == 0
    
    def test_three_person_multiple_intervals(self):
        """Test: 3 participants with multiple intervals."""
        person_a = IntervalSet([
            (9 * 60, 11 * 60),      # 9-11 AM
            (14 * 60, 16 * 60)      # 2-4 PM
        ])
        person_b = IntervalSet([
            (10 * 60, 12 * 60),     # 10-12 AM
            (13 * 60, 17 * 60)      # 1-5 PM
        ])
        person_c = IntervalSet([
            (9 * 60, 10.5 * 60),    # 9-10:30 AM
            (14.5 * 60, 15.5 * 60)  # 2:30-3:30 PM
        ])
        
        result = person_a.and_with(person_b)
        result = result.and_with(person_c)
        
        assert result == IntervalSet([
            (10 * 60, 10.5 * 60),   # 10-10:30 (9-11 ∩ 10-12 ∩ 9-10:30)
            (14.5 * 60, 15.5 * 60)  # 2:30-3:30 (14-16 ∩ 13-17 ∩ 14:30-15:30)
        ])
    
    def test_four_person_and(self):
        """Test: 4 participants."""
        person_a = IntervalSet([(9 * 60, 14 * 60)])
        person_b = IntervalSet([(10 * 60, 15 * 60)])
        person_c = IntervalSet([(9.5 * 60, 14.5 * 60)])
        person_d = IntervalSet([(11 * 60, 13 * 60)])
        
        result = person_a.and_with(person_b).and_with(person_c).and_with(person_d)
        
        assert result == IntervalSet([(11 * 60, 13 * 60)])


class TestEmptyIntersection:
    """Test cases where AND produces empty result."""
    
    def test_one_person_no_overlap(self):
        """Test: Person outside time window."""
        person_a = IntervalSet([(9 * 60, 10 * 60)])
        person_b = IntervalSet([(15 * 60, 16 * 60)])
        
        result = person_a.and_with(person_b)
        
        assert result.intervals == []
        assert result.total_duration() == 0
    
    def test_adjacent_but_not_overlapping(self):
        """Test: Intervals are adjacent but not overlapping."""
        person_a = IntervalSet([(9 * 60, 10 * 60)])  # 9:00-10:00
        person_b = IntervalSet([(10 * 60, 11 * 60)])  # 10:00-11:00
        
        result = person_a.and_with(person_b)
        
        assert result.intervals == []  # No overlap at boundary
        assert result.total_duration() == 0
    
    def test_many_gaps_no_common_slot(self):
        """Test: Many short intervals, no common slot."""
        person_a = IntervalSet([(9 * 60, 9.5 * 60), (11 * 60, 11.5 * 60)])
        person_b = IntervalSet([(9.5 * 60, 10.5 * 60), (12 * 60, 13 * 60)])
        
        result = person_a.and_with(person_b)
        
        assert result.intervals == []


class TestAllFreeTime:
    """Test cases where entire day is free."""
    
    def test_all_day_free(self):
        """Test: All participants free all day."""
        person_a = IntervalSet([(0, 24 * 60)])
        person_b = IntervalSet([(0, 24 * 60)])
        
        result = person_a.and_with(person_b)
        
        assert result == IntervalSet([(0, 24 * 60)])
        assert result.total_duration() == 24 * 60
    
    def test_first_person_limited_others_all_free(self):
        """Test: First person has constraints, others all free."""
        person_a = IntervalSet([(9 * 60, 10 * 60)])
        person_b = IntervalSet([(0, 24 * 60)])  # All free
        
        result = person_a.and_with(person_b)
        
        assert result == IntervalSet([(9 * 60, 10 * 60)])
        assert result.total_duration() == 60


class TestEdgeCases:
    """Test edge cases for AND logic."""
    
    def test_single_minute_overlap(self):
        """Test: Only 1-minute overlap."""
        person_a = IntervalSet([(10 * 60, 11 * 60)])
        person_b = IntervalSet([(10.5 * 60 + 59/60, 12 * 60)])
        
        # Create intervals that overlap by 1 minute
        person_a = IntervalSet([(600, 660)])  # 10:00-11:00
        person_b = IntervalSet([(659, 720)])  # 10:59-12:00
        
        result = person_a.and_with(person_b)
        
        assert result == IntervalSet([(659, 660)])
        assert result.total_duration() == 1
    
    def test_exact_boundary_overlap(self):
        """Test: Exact boundary match."""
        person_a = IntervalSet([(9 * 60, 11 * 60), (14 * 60, 16 * 60)])
        person_b = IntervalSet([(10 * 60, 11 * 60), (14 * 60, 15 * 60)])
        
        result = person_a.and_with(person_b)
        
        assert result == IntervalSet([(10 * 60, 11 * 60), (14 * 60, 15 * 60)])
    
    def test_interval_completely_contained(self):
        """Test: One interval contains another."""
        person_a = IntervalSet([(9 * 60, 16 * 60)])  # 9-4 PM (entire day)
        person_b = IntervalSet([(10 * 60, 11 * 60)])  # 10-11 AM (subset)
        
        result = person_a.and_with(person_b)
        
        assert result == IntervalSet([(10 * 60, 11 * 60)])
        assert result.total_duration() == 60


class TestDurationCalculation:
    """Test duration calculation on AND results."""
    
    def test_single_interval_duration(self):
        """Test: Duration of single interval."""
        intervals = IntervalSet([(9 * 60, 11 * 60)])
        assert intervals.total_duration() == 120
    
    def test_multiple_intervals_duration(self):
        """Test: Total duration across multiple intervals."""
        intervals = IntervalSet([
            (9 * 60, 10 * 60),      # 60 min
            (11 * 60, 13 * 60),     # 120 min
            (14 * 60, 14.5 * 60)    # 30 min
        ])
        assert intervals.total_duration() == 210
    
    def test_empty_duration(self):
        """Test: Duration of empty set."""
        intervals = IntervalSet([])
        assert intervals.total_duration() == 0
