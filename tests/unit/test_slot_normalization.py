"""Unit tests for slot normalization (conservative ceil/floor logic).

Test the 5-minute slot normalization with conservative boundaries:
- Busy interval start: CEILING (exclude the slot it touches)
- Busy interval end: FLOOR (exclude the slot it touches)
"""
import pytest
from src.lib.slot_utils import (
    normalize_busy_interval,
    minutes_to_slots,
    get_conflicting_slots,
    validate_slot_boundaries,
)


class TestNormalizeIntervals:
    """Test conservative normalization (ceiling start, floor end)."""

    def test_normalize_14_30_to_14_55(self):
        """14:30-14:55 should normalize to empty (no complete 30-min slots)."""
        # 14:30 = 870 minutes, 14:55 = 895 minutes
        # 30-min slots: [840-870), [870-900), [900-930)...
        # 870-895 touches [870-900) but doesn't complete it
        # Conservative ceil: 900, floor: 870 → empty
        result = normalize_busy_interval(870, 895, slot_minutes=30)
        assert result == []

    def test_normalize_14_00_to_14_30(self):
        """14:00-14:30 should be normalized correctly."""
        # 14:00 = 840, 14:30 = 870 (1 slot: [840-870))
        result = normalize_busy_interval(840, 870, slot_minutes=30)
        assert (840, 870) in [(s[0], s[1]) for s in result]

    def test_normalize_14_00_to_15_00(self):
        """14:00-15:00 should be 2 slots with 30-min granularity."""
        result = normalize_busy_interval(840, 900, slot_minutes=30)
        assert len(result) == 2  # [840-870), [870-900)

    def test_normalize_9_15_to_9_45(self):
        """9:15-9:45 (conservative ceiling/floor) with 30-min slots."""
        # 9:15 = 555, 9:45 = 585
        # 30-min slots near 9: ..., [510-540), [540-570), [570-600)
        # ceil(555) = 570, floor(585) = 570 → no slots? Need to verify
        result = normalize_busy_interval(555, 585, slot_minutes=30)
        # Conservative: starts at 570, ends at 570 → no complete slot
        assert len(result) == 0

    def test_normalize_8_00_to_12_00(self):
        """Large interval spanning 8-12 with 30-min slots."""
        # 8:00 = 480, 12:00 = 720
        result = normalize_busy_interval(480, 720, slot_minutes=30)
        assert len(result) == 8  # 4 hours = 8 × 30-min slots

    def test_normalize_fractional_start(self):
        """Start time not on slot boundary (9:17 with 30-min slots)."""
        # 9:17 = 557, ceil to next 30-min boundary = 570
        result = normalize_busy_interval(557, 901, slot_minutes=30)
        # Should include [570-600), [600-630), ..., [870-900)
        assert len(result) > 0
        # First slot should start at 570 (or next boundary after ceiling)

    def test_normalize_with_5min_slots(self):
        """Test with 5-minute slot granularity (internal representation)."""
        result = normalize_busy_interval(870, 900, slot_minutes=5)
        # 15 slots of 5 minutes each
        assert len(result) == 6  # 30 minutes = 6 × 5-min slots

    def test_validate_slot_boundaries(self):
        """Test slot boundary validation."""
        # Valid: 5-min aligned
        assert validate_slot_boundaries(0, 5, slot_minutes=5)
        assert validate_slot_boundaries(100, 105, slot_minutes=5)
        
        # Invalid: not aligned
        assert not validate_slot_boundaries(0, 7, slot_minutes=5)
        assert not validate_slot_boundaries(3, 10, slot_minutes=5)


class TestMinutesToSlots:
    """Test conversion of minutes to slot ranges."""

    def test_minutes_to_slots_single(self):
        """Convert single time point to slot."""
        slot = minutes_to_slots(600, slot_minutes=30)
        assert slot == (600, 630)  # 10:00-10:30

    def test_minutes_to_slots_interval(self):
        """Convert interval to slots."""
        slots = minutes_to_slots((600, 900), slot_minutes=30)
        assert len(slots) == 10  # 5 hours

    def test_minutes_to_slots_across_midnight(self):
        """Handle slots near end of day."""
        # 23:00 = 1380, 23:30 = 1410, 00:00 (next day) = 1440
        slot = minutes_to_slots(1380, slot_minutes=30)
        assert slot == (1380, 1410)


class TestConflictingSlots:
    """Test identification of conflicting slots."""

    def test_no_conflicts(self):
        """Non-overlapping intervals have no conflicts."""
        slots1 = [(300, 330), (330, 360)]  # 5:00-6:00
        slots2 = [(600, 630), (630, 660)]  # 10:00-11:00
        conflicts = get_conflicting_slots(slots1, slots2)
        assert len(conflicts) == 0

    def test_exact_overlap(self):
        """Exact overlap detected."""
        slots1 = [(300, 330), (330, 360)]
        slots2 = [(300, 330), (330, 360)]
        conflicts = get_conflicting_slots(slots1, slots2)
        assert len(conflicts) == 2

    def test_partial_overlap(self):
        """Partial overlap detected."""
        slots1 = [(300, 360)]
        slots2 = [(330, 390)]
        conflicts = get_conflicting_slots(slots1, slots2)
        assert len(conflicts) == 1  # [330, 360)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_normalize_zero_duration(self):
        """Zero-duration interval (same start and end)."""
        result = normalize_busy_interval(600, 600, slot_minutes=30)
        assert len(result) == 0

    def test_normalize_one_minute_interval(self):
        """Very short interval (1 minute)."""
        result = normalize_busy_interval(600, 601, slot_minutes=30)
        assert len(result) == 0  # Conservative logic excludes partial slots

    def test_normalize_entire_day(self):
        """Full day interval (00:00-24:00)."""
        result = normalize_busy_interval(0, 1440, slot_minutes=30)
        assert len(result) == 48  # 24 hours = 48 × 30-min slots

    def test_normalize_single_slot(self):
        """Interval exactly matching one slot."""
        result = normalize_busy_interval(600, 630, slot_minutes=30)
        assert len(result) == 1
        assert result[0] == (600, 630)
