"""Availability grid generation service.

Creates full week grid with overlap counts and status per slot.
Generates JSONB structure for FreeTimeResult storage.
"""
import logging
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)


class AvailabilityGrid:
    """Represents availability grid for full week."""
    
    def __init__(
        self,
        total_participants: int,
        slot_minutes: int = 30
    ):
        """Initialize grid.
        
        Args:
            total_participants: Number of participants in group
            slot_minutes: Slot granularity (10/20/30/60)
        """
        self.total_participants = total_participants
        self.slot_minutes = slot_minutes
        self.slots_per_day = (24 * 60) // slot_minutes
        
        logger.info(
            f"Created AvailabilityGrid: {total_participants} participants, "
            f"{slot_minutes}min slots, {self.slots_per_day} slots/day"
        )
    
    def build_grid(self, free_time_by_day: dict) -> Dict[int, List[dict]]:
        """Build availability grid from free-time intervals.
        
        Args:
            free_time_by_day: Dict mapping day_of_week → free-time intervals
        
        Returns:
            Grid dict: {day: [slots]}
            Each slot has: start_minute, end_minute, available, total, percentage
        """
        grid = {}
        
        for day in range(7):
            grid[day] = self._build_day_grid(day, free_time_by_day.get(day, []))
        
        return grid
    
    def _build_day_grid(
        self,
        day_of_week: int,
        intervals: List
    ) -> List[dict]:
        """Build grid for single day.
        
        Args:
            day_of_week: Day number (0-6)
            intervals: Free-time intervals for this day
        
        Returns:
            List of slot dicts
        """
        slots = []
        
        # Create all 30-min (or slot_minutes) slots for the day
        for slot_idx in range(self.slots_per_day):
            start_minute = slot_idx * self.slot_minutes
            end_minute = (slot_idx + 1) * self.slot_minutes
            
            # Count how many participants are available in this slot
            available_count = self._count_available_in_slot(
                start_minute,
                end_minute,
                intervals
            )
            
            slot = {
                "start_minute": start_minute,
                "end_minute": end_minute,
                "available": available_count,
                "total": self.total_participants,
                "percentage": self._calculate_percentage(available_count),
            }
            
            slots.append(slot)
        
        return slots
    
    def _count_available_in_slot(
        self,
        slot_start: int,
        slot_end: int,
        intervals: List
    ) -> int:
        """Count participants available in a time slot.
        
        Args:
            slot_start: Slot start minute
            slot_end: Slot end minute
            intervals: Free-time intervals (all participants combined)
        
        Returns:
            Number of participants available
        """
        # In AND calculation, if interval is in result, ALL participants are free
        # So check if this slot overlaps with any result interval
        for interval in intervals:
            if isinstance(interval, dict):
                interval_start = interval.get("start_minute", 0)
                interval_end = interval.get("end_minute", 0)
            elif isinstance(interval, (list, tuple)):
                interval_start, interval_end = interval[0], interval[1]
            else:
                continue
            
            # Check overlap
            if slot_start < interval_end and slot_end > interval_start:
                return self.total_participants
        
        return 0
    
    def _calculate_percentage(self, available_count: int) -> float:
        """Calculate percentage of available participants.
        
        Args:
            available_count: Number of available participants
        
        Returns:
            Percentage (0.0-100.0) rounded to 1 decimal
        """
        if self.total_participants == 0:
            return 0.0
        
        percentage = (available_count / self.total_participants) * 100
        return round(percentage, 1)
    
    def calculate_day_status(
        self,
        slots: List[dict]
    ) -> dict:
        """Calculate summary status for a day.
        
        Args:
            slots: List of slot dicts for the day
        
        Returns:
            Status dict with availability metrics and categorization
        """
        available_minutes = 0
        total_slots = len(slots)
        available_slots = 0
        
        for slot in slots:
            if slot["available"] > 0:
                available_minutes += slot["end_minute"] - slot["start_minute"]
                available_slots += 1
        
        total_minutes = 24 * 60
        percentage = (available_minutes / total_minutes * 100) if total_minutes > 0 else 0
        
        # Categorize availability
        if percentage == 100:
            status = "completely_free"
        elif percentage >= 75:
            status = "mostly_free"
        elif percentage >= 50:
            status = "partially_free"
        elif percentage > 0:
            status = "mostly_busy"
        else:
            status = "completely_busy"
        
        return {
            "available_minutes": available_minutes,
            "available_hours": round(available_minutes / 60, 1),
            "percentage": round(percentage, 1),
            "available_slots": available_slots,
            "total_slots": total_slots,
            "status": status,
        }
    
    def build_status_by_day(self, grid: Dict[int, List[dict]]) -> Dict[int, dict]:
        """Build status summary for each day.
        
        Args:
            grid: Full week grid
        
        Returns:
            Dict mapping day → status dict
        """
        status_by_day = {}
        
        day_names = [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ]
        
        for day in range(7):
            slots = grid.get(day, [])
            status = self.calculate_day_status(slots)
            status["day_name"] = day_names[day]
            status_by_day[day] = status
        
        return status_by_day
    
    def to_jsonb(self, grid: Dict[int, List[dict]]) -> str:
        """Convert grid to JSONB string for database storage.
        
        Args:
            grid: Full week grid
        
        Returns:
            JSON string
        """
        try:
            jsonb_str = json.dumps(grid)
            size_bytes = len(jsonb_str.encode('utf-8'))
            logger.info(f"JSONB grid size: {size_bytes} bytes")
            return jsonb_str
        except Exception as e:
            logger.error(f"Failed to serialize grid to JSONB: {e}", exc_info=True)
            return json.dumps({})
    
    def get_day_availability(self, grid: Dict[int, List[dict]], day: int) -> dict:
        """Get availability info for specific day.
        
        Args:
            grid: Full week grid
            day: Day of week (0-6)
        
        Returns:
            Dict with slots and statistics
        """
        slots = grid.get(day, [])
        status = self.calculate_day_status(slots)
        
        return {
            "day": day,
            "slots": slots,
            "status": status,
        }
    
    def get_peak_availability_windows(
        self,
        grid: Dict[int, List[dict]],
        window_size_hours: int = 1
    ) -> List[dict]:
        """Find time windows with peak availability.
        
        Args:
            grid: Full week grid
            window_size_hours: Size of window to search (hours)
        
        Returns:
            List of peak windows, ranked by availability
        """
        window_minutes = window_size_hours * 60
        windows = []
        
        for day in range(7):
            slots = grid.get(day, [])
            
            # Scan through day in window_size_hours sliding windows
            for window_start_idx in range(len(slots) - (window_minutes // self.slot_minutes) + 1):
                window_end_idx = window_start_idx + (window_minutes // self.slot_minutes)
                window_slots = slots[window_start_idx:window_end_idx]
                
                # Calculate availability in this window
                available_in_window = sum(s["available"] for s in window_slots)
                max_possible = self.total_participants * len(window_slots)
                
                if available_in_window > 0:
                    window = {
                        "day": day,
                        "start_minute": window_slots[0]["start_minute"],
                        "end_minute": window_slots[-1]["end_minute"],
                        "available": available_in_window,
                        "total": max_possible,
                        "percentage": round(
                            (available_in_window / max_possible) * 100, 1
                        ) if max_possible > 0 else 0,
                    }
                    windows.append(window)
        
        # Sort by availability percentage (descending)
        windows = sorted(
            windows,
            key=lambda w: (-w["percentage"], w["day"], w["start_minute"])
        )
        
        return windows[:10]  # Return top 10


class GridGenerator:
    """Service to generate full availability grid."""
    
    def __init__(self, total_participants: int, slot_minutes: int = 30):
        """Initialize generator.
        
        Args:
            total_participants: Group size
            slot_minutes: Display unit granularity
        """
        self.grid = AvailabilityGrid(total_participants, slot_minutes)
    
    def generate(self, free_time_by_day: dict) -> dict:
        """Generate complete availability grid.
        
        Args:
            free_time_by_day: Dict mapping day → intervals
        
        Returns:
            Complete grid for storage
        """
        grid = self.grid.build_grid(free_time_by_day)
        status_by_day = self.grid.build_status_by_day(grid)
        
        result = {
            "grid": grid,
            "status_by_day": status_by_day,
            "summary": self._calculate_summary(status_by_day),
        }
        
        return result
    
    def _calculate_summary(self, status_by_day: dict) -> dict:
        """Calculate overall summary statistics.
        
        Args:
            status_by_day: Status dict for each day
        
        Returns:
            Summary statistics
        """
        total_available_hours = 0
        days_with_availability = 0
        
        for day, status in status_by_day.items():
            total_available_hours += status.get("available_hours", 0)
            if status.get("available_hours", 0) > 0:
                days_with_availability += 1
        
        return {
            "total_available_hours": round(total_available_hours, 1),
            "days_with_availability": days_with_availability,
            "average_hours_per_day": round(
                total_available_hours / 7, 1
            ) if total_available_hours > 0 else 0,
        }
