"""
Pydantic schemas for free-time response (T057, T059)

Response structure per openapi.yaml:
- FreeTimeResponse: Main response with group, participants, free-time, grid
- FreeTimeSlot: Individual time slot with day, time window, overlap count
- AvailabilityGrid: Full week grid with JSONB structure
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ParticipantInfo(BaseModel):
    """Participant information in response."""
    nickname: str = Field(..., description="Participant's nickname")
    submitted_at: str = Field(..., description="Submission timestamp (ISO 8601)")


class FreeTimeSlot(BaseModel):
    """Single free-time slot."""
    day: str = Field(
        ...,
        enum=["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"],
        description="Day of week"
    )
    start_minute: int = Field(..., description="Start time in minutes from 00:00 (0-1439)")
    end_minute: int = Field(..., description="End time in minutes from 00:00 (0-1439)")
    duration_minutes: int = Field(..., description="Duration of free-time slot (minutes)")
    overlap_count: int = Field(..., description="Number of participants available in this slot")


class AvailabilitySlot(BaseModel):
    """Individual slot in JSONB availability grid."""
    slot_id: str = Field(..., description="Unique identifier for this slot")
    time_window: Dict[str, Any] = Field(
        ...,
        description="Time window {start_minute, end_minute}"
    )
    availability_count: int = Field(
        ...,
        description="How many participants are available"
    )
    is_common: bool = Field(
        ...,
        description="True if all participants are available"
    )


class AvailabilityByDay(BaseModel):
    """JSONB structure for availability grid by day."""

    class Config:
        extra = "allow"  # Allow dynamic day keys
    
    # Days as optional fields (schema allows any day key)
    # Example: { "MONDAY": [...], "TUESDAY": [...] }


class FreeTimeResponse(BaseModel):
    """
    Complete free-time polling response (T057, T059).
    
    Includes:
    - Group information
    - Participant list
    - Free-time slots array (3 versions by minimum duration)
    - Availability grid JSONB
    - Computation and expiration timestamps
    """
    group_id: str = Field(..., description="Group UUID")
    group_name: str = Field(..., description="Group name")
    participant_count: int = Field(..., description="Number of participants with submissions")
    participants: List[ParticipantInfo] = Field(
        default_factory=list,
        description="List of participants with nicknames and submission times"
    )
    free_time: List[FreeTimeSlot] = Field(
        default_factory=list,
        description="Array of free-time slots (≥10 minutes minimum)"
    )
    free_time_30min: List[FreeTimeSlot] = Field(
        default_factory=list,
        description="Array of free-time slots (≥30 minutes minimum)"
    )
    free_time_60min: List[FreeTimeSlot] = Field(
        default_factory=list,
        description="Array of free-time slots (≥60 minutes minimum)"
    )
    availability_by_day: Optional[Dict[str, List[Dict[str, Any]]]] = Field(
        default_factory=dict,
        description="JSONB: Slot-by-slot availability grid for web heatmap (T059)"
    )
    computed_at: Optional[str] = Field(
        None,
        description="Calculation timestamp (ISO 8601 with Z suffix)"
    )
    expires_at: str = Field(
        ...,
        description="Group expiration timestamp (ISO 8601 with Z suffix)"
    )
    display_unit_minutes: int = Field(
        ...,
        description="Display unit for time slots (10, 20, 30, or 60 minutes)"
    )
    version: int = Field(
        default=0,
        description="Calculation result version (incremented on recalculation)"
    )
    )

    class Config:
        schema_extra = {
            "example": {
                "group_id": "550e8400-e29b-41d4-a716-446655440000",
                "group_name": "study_group",
                "participant_count": 3,
                "participants": [
                    {
                        "nickname": "happy_blue_lion",
                        "submitted_at": "2026-02-13T10:00:00Z"
                    },
                    {
                        "nickname": "swift_silver_mountain",
                        "submitted_at": "2026-02-13T10:05:00Z"
                    }
                ],
                "free_time": [
                    {
                        "day": "MONDAY",
                        "start_minute": 840,
                        "end_minute": 930,
                        "duration_minutes": 90,
                        "overlap_count": 3
                    }
                ],
                "availability_by_day": {
                    "MONDAY": [
                        {
                            "slot_id": "MON_14_00",
                            "time_window": {"start_minute": 840, "end_minute": 900},
                            "availability_count": 3,
                            "is_common": True
                        },
                        {
                            "slot_id": "MON_14_30",
                            "time_window": {"start_minute": 870, "end_minute": 930},
                            "availability_count": 2,
                            "is_common": False
                        }
                    ]
                },
                "computed_at": "2026-02-13T10:10:00Z",
                "expires_at": "2026-02-16T10:00:00Z",
                "display_unit_minutes": 30,
                "version": 1
            }
        }
