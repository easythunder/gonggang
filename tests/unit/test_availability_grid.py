"""Unit tests for availability grid generation.

Tests the full week grid with overlap counts and JSONB structure.
"""
import pytest
import json
from typing import Dict, List


class AvailabilitySlot:
    """Represents one slot in availability grid."""
    
    def __init__(
        self,
        day_of_week: int,
        start_minute: int,
        end_minute: int,
        available_participants: int,
        total_participants: int
    ):
        self.day_of_week = day_of_week
        self.start_minute = start_minute
        self.end_minute = end_minute
        self.available_participants = available_participants
        self.total_participants = total_participants
    
    @property
    def availability_percentage(self) -> float:
        """Percentage of participants available."""
        if self.total_participants == 0:
            return 0.0
        return (self.available_participants / self.total_participants) * 100
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSONB storage."""
        return {
            "start_minute": self.start_minute,
            "end_minute": self.end_minute,
            "available": self.available_participants,
            "total": self.total_participants,
            "percentage": round(self.availability_percentage, 1)
        }
    
    def __repr__(self):
        return f"Slot(day={self.day_of_week}, {self.start_minute}-{self.end_minute}, {self.available_participants}/{self.total_participants})"


class TestGridStructure:
    """Test availability grid structure and layout."""
    
    def test_grid_has_seven_days(self):
        """Test: Grid has entries for 7 days."""
        grid = create_empty_grid(total_participants=2)
        
        assert len(grid) == 7
        for day in range(7):
            assert day in grid
    
    def test_grid_has_all_slots(self):
        """Test: Grid has all 30-minute slots for each day."""
        grid = create_empty_grid(total_participants=2, slot_minutes=30)
        
        for day in range(7):
            slots = grid[day]
            # 24 * 60 / 30 = 48 slots
            assert len(slots) == 48
    
    def test_grid_with_10_min_slots(self):
        """Test: Grid with 10-minute slots."""
        grid = create_empty_grid(total_participants=2, slot_minutes=10)
        
        for day in range(7):
            slots = grid[day]
            # 24 * 60 / 10 = 144 slots
            assert len(slots) == 144
    
    def test_grid_slot_coverage(self):
        """Test: Each slot covers exactly slot_minutes duration."""
        grid = create_empty_grid(total_participants=2, slot_minutes=30)
        
        for day in range(7):
            for i, slot in enumerate(grid[day]):
                expected_start = i * 30
                expected_end = (i + 1) * 30
                
                assert slot['start_minute'] == expected_start
                assert slot['end_minute'] == expected_end
    
    def test_grid_no_gaps_or_overlaps(self):
        """Test: Grid slots have no gaps or overlaps."""
        grid = create_empty_grid(total_participants=2, slot_minutes=30)
        
        for day in range(7):
            slots = grid[day]
            for i in range(len(slots) - 1):
                current_end = slots[i]['end_minute']
                next_start = slots[i + 1]['start_minute']
                assert current_end == next_start  # No gap


class TestOverlapCounts:
    """Test overlap count calculations in grid."""
    
    def test_all_available_slots(self):
        """Test: Slots where all participants are available."""
        grid = create_grid_from_intervals(
            total_participants=3,
            intervals=[
                [(0, 1 * 60), (1 * 60, 2 * 60)],  # Person 1: 0-2 AM
                [(0, 1 * 60), (1 * 60, 2 * 60)],  # Person 2: 0-2 AM
                [(0, 1 * 60), (1 * 60, 2 * 60)],  # Person 3: 0-2 AM
            ],
            slot_minutes=30
        )
        
        # Check first day
        slots = grid[0]
        assert slots[0]['available'] == 3  # 0:00-0:30
        assert slots[0]['total'] == 3
        assert slots[1]['available'] == 3  # 0:30-1:00
        assert slots[2]['available'] == 3  # 1:00-1:30
    
    def test_partial_overlap(self):
        """Test: Slots with partial participant overlap."""
        grid = create_grid_from_intervals(
            total_participants=3,
            intervals=[
                [(9 * 60, 11 * 60)],    # Person 1: 9-11 AM
                [(10 * 60, 12 * 60)],   # Person 2: 10 AM-12 PM
                [],                      # Person 3: no availability
            ],
            slot_minutes=30
        )
        
        slots = grid[0]
        
        # 9:00-9:30: only person 1 available
        idx_9am = 9 * 2  # 30-min slot index for 9 AM
        assert slots[idx_9am]['available'] == 1
        assert slots[idx_9am]['total'] == 3
        
        # 10:00-10:30: both persons 1 and 2 available
        idx_10am = 10 * 2
        assert slots[idx_10am]['available'] == 2
        assert slots[idx_10am]['total'] == 3
    
    def test_no_availability(self):
        """Test: Slot where no one is available."""
        grid = create_grid_from_intervals(
            total_participants=2,
            intervals=[
                [(9 * 60, 10 * 60)],    # Person 1: 9-10 AM
                [(14 * 60, 15 * 60)],   # Person 2: 2-3 PM
            ],
            slot_minutes=30
        )
        
        slots = grid[0]
        
        # 11:00-11:30: nobody available
        idx_11am = 11 * 2
        assert slots[idx_11am]['available'] == 0
        assert slots[idx_11am]['total'] == 2


class TestAvailabilityPercentage:
    """Test percentage calculations in grid."""
    
    def test_percentage_all_available(self):
        """Test: 100% when all available."""
        slot = AvailabilitySlot(0, 540, 600, 3, 3)
        assert slot.availability_percentage == 100.0
    
    def test_percentage_partial(self):
        """Test: Partial percentage calculations."""
        slot = AvailabilitySlot(0, 540, 600, 2, 4)
        assert slot.availability_percentage == 50.0
    
    def test_percentage_none_available(self):
        """Test: 0% when none available."""
        slot = AvailabilitySlot(0, 540, 600, 0, 4)
        assert slot.availability_percentage == 0.0
    
    def test_percentage_one_of_many(self):
        """Test: One person available out of many."""
        slot = AvailabilitySlot(0, 540, 600, 1, 10)
        assert slot.availability_percentage == 10.0
    
    def test_percentage_rounding(self):
        """Test: Percentage rounding to 1 decimal."""
        slot = AvailabilitySlot(0, 540, 600, 1, 3)
        assert slot.availability_percentage == pytest.approx(33.333, rel=0.01)
        assert round(slot.availability_percentage, 1) == 33.3


class TestStatusByDay:
    """Test day-level status summarization."""
    
    def test_day_status_all_free(self):
        """Test: Day status when entirely free."""
        slots = [
            {'available': 3, 'total': 3, 'start_minute': i * 30, 'end_minute': (i + 1) * 30}
            for i in range(48)  # 48 x 30-min slots = full day
        ]
        
        day_status = calculate_day_status(slots, 3)
        
        assert day_status['available_minutes'] == 24 * 60
        assert day_status['percentage'] == 100.0
        assert day_status['status'] == 'completely_free'
    
    def test_day_status_partially_free(self):
        """Test: Day status when partially free."""
        # 12 hours free, 12 hours busy
        slots = []
        for i in range(48):
            if i < 24:  # First 12 hours (24 x 30-min slots)
                slots.append({'available': 3, 'total': 3, 'start_minute': i * 30, 'end_minute': (i + 1) * 30})
            else:
                slots.append({'available': 0, 'total': 3, 'start_minute': i * 30, 'end_minute': (i + 1) * 30})
        
        day_status = calculate_day_status(slots, 3)
        
        assert day_status['available_minutes'] == 12 * 60
        assert day_status['percentage'] == 50.0
        assert day_status['status'] == 'partially_free'
    
    def test_day_status_busy(self):
        """Test: Day status when busy."""
        slots = [
            {'available': 1, 'total': 3, 'start_minute': i * 30, 'end_minute': (i + 1) * 30}
            for i in range(48)
        ]
        
        day_status = calculate_day_status(slots, 3)
        
        assert day_status['status'] == 'busy'
    
    def test_day_status_no_availability(self):
        """Test: Day status when no availability."""
        slots = [
            {'available': 0, 'total': 3, 'start_minute': i * 30, 'end_minute': (i + 1) * 30}
            for i in range(48)
        ]
        
        day_status = calculate_day_status(slots, 3)
        
        assert day_status['available_minutes'] == 0
        assert day_status['percentage'] == 0.0
        assert day_status['status'] == 'completely_busy'


class TestJsonbSerialization:
    """Test JSONB serialization of grid."""
    
    def test_grid_to_jsonb(self):
        """Test: Grid converts to valid JSONB."""
        grid = create_empty_grid(total_participants=2, slot_minutes=30)
        
        jsonb_str = json.dumps(grid)
        parsed = json.loads(jsonb_str)
        
        assert isinstance(parsed, dict)
        assert len(parsed) == 7
    
    def test_grid_contains_required_fields(self):
        """Test: Each slot has required JSONB fields."""
        grid = create_grid_from_intervals(
            total_participants=2,
            intervals=[[(9 * 60, 10 * 60)], [(10 * 60, 11 * 60)]],
            slot_minutes=30
        )
        
        for day in range(7):
            for slot in grid[day]:
                assert 'start_minute' in slot
                assert 'end_minute' in slot
                assert 'available' in slot
                assert 'total' in slot
                assert 'percentage' in slot
    
    def test_grid_large_jsonb_size(self):
        """Test: Large grid (many participants, fine granularity) serializes efficiently."""
        grid = create_grid_from_intervals(
            total_participants=50,
            intervals=[[(i * 60, (i + 1) * 60) for i in range(9, 17)]
                      for _ in range(50)],  # 50 people free 9-5
            slot_minutes=5  # Fine-grained: 288 slots/day
        )
        
        jsonb_str = json.dumps(grid)
        size_bytes = len(jsonb_str.encode('utf-8'))
        
        # Should be reasonably sized (not in MB range)
        assert size_bytes < 1_000_000  # Less than 1MB


# Helper functions

def create_empty_grid(
    total_participants: int,
    slot_minutes: int = 30
) -> Dict[int, List[dict]]:
    """Create empty grid with all slots at 0 availability."""
    grid = {}
    slots_per_day = (24 * 60) // slot_minutes
    
    for day in range(7):
        grid[day] = []
        for slot_idx in range(slots_per_day):
            start = slot_idx * slot_minutes
            end = (slot_idx + 1) * slot_minutes
            
            grid[day].append({
                'start_minute': start,
                'end_minute': end,
                'available': 0,
                'total': total_participants,
                'percentage': 0.0
            })
    
    return grid


def create_grid_from_intervals(
    total_participants: int,
    intervals: List[List[tuple]],  # intervals[person] = [(start, end), ...]
    slot_minutes: int = 30
) -> Dict[int, List[dict]]:
    """Create grid from participant availability intervals."""
    grid = create_empty_grid(total_participants, slot_minutes)
    slots_per_day = (24 * 60) // slot_minutes
    
    # Initialize all slots with 0 available
    for day in range(7):
        for slot_idx in range(slots_per_day):
            grid[day][slot_idx]['available'] = 0
    
    # Mark availability for each person
    for person_idx, person_intervals in enumerate(intervals):
        for start_minute, end_minute in person_intervals:
            # Find all slots that overlap with this interval
            for day in range(7):
                for slot_idx in range(slots_per_day):
                    slot_start = slot_idx * slot_minutes
                    slot_end = (slot_idx + 1) * slot_minutes
                    
                    # Check if slot overlaps with interval
                    if slot_start < end_minute and slot_end > start_minute:
                        grid[day][slot_idx]['available'] += 1
    
    # Recalculate percentages
    for day in range(7):
        for slot in grid[day]:
            if total_participants > 0:
                slot['percentage'] = round(
                    (slot['available'] / total_participants) * 100, 1
                )
    
    return grid


def calculate_day_status(slots: List[dict], total_participants: int) -> dict:
    """Calculate summary status for a day."""
    available_minutes = 0
    
    for slot in slots:
        if slot['available'] > 0:
            available_minutes += slot['end_minute'] - slot['start_minute']
    
    total_minutes = 24 * 60
    percentage = (available_minutes / total_minutes) * 100 if total_minutes > 0 else 0
    
    if percentage == 100:
        status = 'completely_free'
    elif percentage > 50:
        status = 'mostly_free'
    elif percentage > 0:
        status = 'partially_free'
    elif percentage == 0 and available_minutes == 0:
        status = 'completely_busy'
    else:
        status = 'busy'
    
    return {
        'available_minutes': available_minutes,
        'percentage': round(percentage, 1),
        'status': status
    }
