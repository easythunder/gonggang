"""Slot normalization utilities for the 5-minute internal representation.

Conservative logic (as specified):
- Busy interval START: CEILING (move up to next slot boundary) → exclude the slot it touches
- Busy interval END: FLOOR (move down to previous slot boundary) → exclude the slot it touches

Example: 9:15-9:45 with 30-min slots
- Slots: [9:00-9:30), [9:30-10:00), ...
- Busy 9:15-9:45 spans partial slots
- ceil(9:15) = 9:30, floor(9:45) = 9:30 → No complete slots → Empty result
"""
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

MINUTES_PER_DAY = 1440  # 0-1439
SLOT_MINUTES_INTERNAL = 5  # Always 5-minute granularity in DB


def normalize_busy_interval(
    start_minute: int,
    end_minute: int,
    slot_minutes: int = 30,
) -> List[Tuple[int, int]]:
    """Normalize a busy interval to slot boundaries (conservative logic).
    
    Args:
        start_minute: Start time in minutes (0-1439)
        end_minute: End time in minutes (0-1439)
        slot_minutes: Display slot granularity (10, 20, 30, 60) - used for calculation
    
    Returns:
        List of (start_minute, end_minute) tuples representing busy slots
        Each tuple is a complete slot that doesn't overlap with the busy interval
    
    Conservative logic:
        - START: CEILING to next slot boundary (exclude partial start)
        - END: FLOOR to previous slot boundary (exclude partial end)
    """
    if start_minute >= end_minute or start_minute < 0 or end_minute > MINUTES_PER_DAY:
        logger.warning(f"Invalid interval: {start_minute}-{end_minute}")
        return []

    # Apply conservative ceiling/floor logic
    # Ceiling: round UP start to next slot boundary
    normalized_start = ((start_minute + slot_minutes - 1) // slot_minutes) * slot_minutes
    
    # Floor: round DOWN end to previous slot boundary
    normalized_end = (end_minute // slot_minutes) * slot_minutes

    logger.debug(
        f"Normalize {start_minute}-{end_minute} (slot {slot_minutes}min): "
        f"{normalized_start}-{normalized_end}"
    )

    # If normalized start >= end, no complete slots
    if normalized_start >= normalized_end:
        logger.debug("No complete slots after conservative normalization")
        return []

    # Generate list of slots
    slots = []
    current = normalized_start
    while current < normalized_end:
        slot_end = min(current + slot_minutes, normalized_end)
        slots.append((current, slot_end))
        current = slot_end

    return slots


def convert_to_internal_slots(
    start_minute: int,
    end_minute: int,
) -> List[Tuple[int, int]]:
    """Convert normalized slots to internal 5-minute representation.
    
    Args:
        start_minute: Start in any granularity (10/20/30/60)
        end_minute: End in any granularity
    
    Returns:
        List of 5-minute slots
    """
    slots = []
    current = start_minute
    while current < end_minute:
        slot_end = min(current + SLOT_MINUTES_INTERNAL, end_minute)
        slots.append((current, slot_end))
        current = slot_end
    return slots


def minutes_to_slots(
    minutes: int,
    slot_minutes: int = 30,
) -> Tuple[int, int]:
    """Convert a minute value to its slot boundaries.
    
    Args:
        minutes: Point in time (0-1439)
        slot_minutes: Slot granularity
    
    Returns:
        (slot_start, slot_end) tuple
    """
    slot_start = (minutes // slot_minutes) * slot_minutes
    slot_end = slot_start + slot_minutes
    return (slot_start, min(slot_end, MINUTES_PER_DAY))


def validate_slot_boundaries(
    start: int,
    end: int,
    slot_minutes: int = 5,
) -> bool:
    """Check if start and end are aligned to slot boundaries.
    
    Args:
        start: Start minute
        end: End minute
        slot_minutes: Slot size (5, 10, 20, 30, 60)
    
    Returns:
        True if both boundaries are properly aligned
    """
    if start < 0 or end > MINUTES_PER_DAY or start >= end:
        return False
    
    return (start % slot_minutes == 0) and (end % slot_minutes == 0)


def get_conflicting_slots(
    slots1: List[Tuple[int, int]],
    slots2: List[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """Find overlapping slots between two lists.
    
    Args:
        slots1: List of (start, end) slots
        slots2: List of (start, end) slots
    
    Returns:
        List of overlapping (start, end) slots
    """
    conflicts = []
    for s1_start, s1_end in slots1:
        for s2_start, s2_end in slots2:
            # Check overlap
            overlap_start = max(s1_start, s2_start)
            overlap_end = min(s1_end, s2_end)
            if overlap_start < overlap_end:
                conflicts.append((overlap_start, overlap_end))
    
    return conflicts


def merge_adjacent_slots(
    slots: List[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """Merge adjacent/overlapping slots into continuous ranges.
    
    Args:
        slots: List of (start, end) slots (must be sorted)
    
    Returns:
        Merged list of slots
    """
    if not slots:
        return []
    
    # Sort by start time
    sorted_slots = sorted(slots, key=lambda s: s[0])
    merged = [sorted_slots[0]]
    
    for current_start, current_end in sorted_slots[1:]:
        last_start, last_end = merged[-1]
        
        # If current overlaps or is adjacent to last
        if current_start <= last_end:
            # Merge
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            # Add as new slot
            merged.append((current_start, current_end))
    
    return merged


def duration_to_hhmm(minutes: int) -> str:
    """Convert duration in minutes to HH:MM format.
    
    Args:
        minutes: Duration in minutes
    
    Returns:
        String in HH:MM format
    """
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def minute_to_hhmm(minute: int) -> str:
    """Convert minute (0-1439) to HH:MM format.
    
    Args:
        minute: Time in minutes since midnight
    
    Returns:
        String in HH:MM format
    """
    if minute < 0 or minute >= MINUTES_PER_DAY:
        return "INVALID"
    
    hours = minute // 60
    mins = minute % 60
    return f"{hours:02d}:{mins:02d}"


def hhmm_to_minute(hhmm: str) -> Optional[int]:
    """Convert HH:MM format to minutes (0-1439).
    
    Args:
        hhmm: String in HH:MM format
    
    Returns:
        Minutes since midnight, or None if invalid
    """
    try:
        parts = hhmm.split(":")
        if len(parts) != 2:
            return None
        
        hours = int(parts[0])
        mins = int(parts[1])
        
        total = hours * 60 + mins
        if 0 <= total < MINUTES_PER_DAY:
            return total
        
        return None
    except (ValueError, AttributeError):
        return None


def slots_to_duration(slots: List[Tuple[int, int]]) -> int:
    """Calculate total duration from list of slots.
    
    Args:
        slots: List of (start, end) slots
    
    Returns:
        Total duration in minutes
    """
    return sum(end - start for start, end in slots)
