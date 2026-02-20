"""Shared utility functions and helpers."""
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def generate_uuid() -> uuid.UUID:
    """Generate a new UUID."""
    return uuid.uuid4()


def to_iso_datetime(dt: datetime) -> str:
    """Convert datetime to ISO 8601 string."""
    return dt.isoformat() if dt else None


def from_iso_datetime(dt_str: str) -> Optional[datetime]:
    """Convert ISO 8601 string to datetime."""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def paginate(
    items: list,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """Create pagination response."""
    return {
        "items": items[offset : offset + limit],
        "total": len(items),
        "limit": limit,
        "offset": offset,
    }


def format_response(
    status: str,
    data: Optional[Any] = None,
    message: Optional[str] = None,
    error: Optional[str] = None,
) -> Dict[str, Any]:
    """Format a standard API response."""
    response = {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if data is not None:
        response["data"] = data

    if message:
        response["message"] = message

    if error:
        response["error"] = error

    return response


class ErrorCodes:
    """Standard error codes for API responses."""

    # 4xx errors
    BAD_REQUEST = "BAD_REQUEST"
    INVALID_INPUT = "INVALID_INPUT"
    GROUP_NOT_FOUND = "GROUP_NOT_FOUND"
    SUBMISSION_NOT_FOUND = "SUBMISSION_NOT_FOUND"
    INTERVAL_NOT_FOUND = "INTERVAL_NOT_FOUND"
    DUPLICATE_SUBMISSION = "DUPLICATE_SUBMISSION"
    MAX_PARTICIPANTS_EXCEEDED = "MAX_PARTICIPANTS_EXCEEDED"

    # 5xx errors
    OCR_TIMEOUT = "OCR_TIMEOUT"
    OCR_FAILED = "OCR_FAILED"
    CALCULATION_FAILED = "CALCULATION_FAILED"
    DATABASE_ERROR = "DATABASE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # Custom
    GROUP_EXPIRED = "GROUP_EXPIRED"
    INVALID_DISPLAY_UNIT = "INVALID_DISPLAY_UNIT"


def validate_display_unit(minutes: int) -> bool:
    """Validate display unit minutes."""
    from src.config import config
    return minutes in config.DISPLAY_UNIT_OPTIONS


def minutes_to_hhmm(minutes: int) -> str:
    """Convert minutes (0-1439) to HH:MM format."""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def hhmm_to_minutes(hhmm: str) -> Optional[int]:
    """Convert HH:MM format to minutes (0-1439)."""
    try:
        parts = hhmm.split(":")
        if len(parts) != 2:
            return None
        hours = int(parts[0])
        mins = int(parts[1])
        total_mins = hours * 60 + mins
        return total_mins if 0 <= total_mins <= 1439 else None
    except (ValueError, IndexError):
        return None


def day_number_to_name(day: int) -> str:
    """Convert day number (0-6) to name (Monday-Sunday)."""
    days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
    return days[day] if 0 <= day <= 6 else "UNKNOWN"


def day_name_to_number(day_name: str) -> Optional[int]:
    """Convert day name to number (0-6)."""
    days = {
        "MONDAY": 0,
        "TUESDAY": 1,
        "WEDNESDAY": 2,
        "THURSDAY": 3,
        "FRIDAY": 4,
        "SATURDAY": 5,
        "SUNDAY": 6,
    }
    return days.get(day_name.upper())
