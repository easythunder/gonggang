"""
Free-time results API endpoints (T056-T060)

GET /groups/{groupId}/free-time: Poll for current free-time calculation results
- Lazy expiration check (410 if expired)
- Server-enforced polling interval (2000-3000ms in header)
- Response structure with availability grid and participants
"""
import logging
import time
from datetime import datetime
from uuid import UUID
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from src.lib.database import db_manager
from src.lib.polling import PollingIntervalEnforcer
from src.lib.utils import format_response
from src.services.group import GroupService
from src.services.free_time import FreeTimeService
from src.templates.free_time import render_free_time_template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groups", tags=["Results"])


# Response schemas
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


class FreeTimeResponse(BaseModel):
    """
    Complete free-time polling response (T057, T059).
    
    Includes:
    - Group information
    - Participant list
    - Free-time slots array
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
        description="Array of common free-time slots"
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


def check_group_expiration(group_id: UUID) -> Dict[str, Any]:
    """
    Check if group has expired via lazy expiration.
    
    Args:
        group_id: Group ID to check
    
    Returns:
        Dict with group info if valid
    
    Raises:
        HTTPException: 404 if not found, 410 if expired
    """
    db = db_manager.get_session()
    try:
        from src.models.group import Group
        group = db.query(Group).filter(Group.id == group_id).first()
        
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # T056: Lazy expiration check
        if group.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=410,
                detail=format_response(
                    "error",
                    error="group_expired",
                    message="This group has expired and all data has been deleted"
                )
            )
        
        return {"group": group, "db": db}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error checking group expiration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{groupId}/free-time")
async def get_group_free_time(
    groupId: UUID,
    interval_ms: Optional[int] = Query(None, description="Client's requested interval (ignored)")
) -> FreeTimeResponse:
    """
    Poll for current free-time calculation results.
    
    Server enforces 2-3 second polling interval regardless of client request.
    
    Args:
        groupId: Group ID
        interval_ms: Client's requested interval (server ignores and enforces 2-3s)
    
    Returns:
        FreeTimeResponse: Current free-time results with response headers
    
    Raises:
        HTTPException: 404 if group not found, 410 if expired
    """
    request_start = time.time()
    
    # T056: Lazy expiration check and get group
    context = check_group_expiration(groupId)
    group = context["group"]
    db = context["db"]
    
    try:
        from src.models.free_time_result import FreeTimeResult
        from src.models.submission import Submission
        
        # Get latest calculation result
        result = db.query(FreeTimeResult).filter(
            FreeTimeResult.group_id == groupId
        ).order_by(FreeTimeResult.version.desc()).first()
        
        # Get all participants (successful submissions)
        participants = db.query(Submission).filter(
            Submission.group_id == groupId,
            Submission.status == "success"
        ).all()
        
        # T057: Build participant list
        participants_info = [
            ParticipantInfo(
                nickname=p.nickname,
                submitted_at=p.created_at.isoformat() + "Z"
            )
            for p in sorted(participants, key=lambda p: p.created_at)
        ]
        
        # T057: Build free time slots
        free_time_slots = []
        availability_by_day = {}
        if result and result.free_time_intervals:
            for interval in result.free_time_intervals:
                free_time_slots.append(FreeTimeSlot(
                    day=interval["day"],
                    start_minute=interval["start_minute"],
                    end_minute=interval["end_minute"],
                    duration_minutes=interval["duration_minutes"],
                    overlap_count=interval.get("overlap_count", len(participants))
                ))
        
        # T059: Get availability grid JSONB
        if result and result.availability_by_day:
            availability_by_day = result.availability_by_day
        
        # Build response
        response = FreeTimeResponse(
            group_id=str(group.id),
            group_name=group.group_name,
            participant_count=len(participants),
            participants=participants_info,
            free_time=free_time_slots,
            availability_by_day=availability_by_day,
            computed_at=(result.computed_at.isoformat() + "Z") if result else None,
            expires_at=group.expires_at.isoformat() + "Z",
            display_unit_minutes=group.display_unit_minutes,
            version=result.version if result else 0
        )
        
        # T058: Server-enforced polling interval
        poll_wait = PollingIntervalEnforcer.validate_and_ignore_client_interval(interval_ms)
        
        # T060: Calculate response time header
        response_time_ms = int((time.time() - request_start) * 1000)
        
        # T060: Build response with headers
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=response.dict(),
            status_code=200,
            headers={
                "X-Poll-Wait": str(poll_wait),
                "X-Response-Time": str(response_time_ms),
                "X-Calculation-Version": str(result.version if result else 0)
            }
        )
    finally:
        db_manager.close_session(db)


@router.get("/{groupId}")
async def get_group_info(groupId: UUID):
    """
    Get group information (not including calculation results).
    
    Args:
        groupId: Group ID
    
    Returns:
        GroupResponse: Group information
    
    Raises:
        HTTPException: 404 if not found, 410 if expired
    """
    context = check_group_expiration(groupId)
    group = context["group"]
    db = context["db"]
    
    try:
        from src.models.submission import Submission
        
        submission_count = db.query(Submission).filter(
            Submission.group_id == groupId,
            Submission.status == "success"
        ).count()
        
        return format_response(
            "success",
            data={
                "group_id": str(group.id),
                "group_name": group.group_name,
                "created_at": group.created_at.isoformat() + "Z",
                "last_activity_at": group.last_activity_at.isoformat() + "Z",
                "expires_at": group.expires_at.isoformat() + "Z",
                "invite_url": group.invite_url,
                "share_url": group.share_url,
                "display_unit_minutes": group.display_unit_minutes,
                "max_participants": group.max_participants,
                "participant_count": submission_count
            }
        )
    finally:
        db_manager.close_session(db)


# HTML endpoint for browser viewing (T061)
@router.get("/{groupId}/view")
async def view_group_free_time_html(groupId: UUID):
    """
    View free-time results as HTML page (T061).
    
    Shows candidate cards, weekly grid heatmap, and participants list.
    
    Args:
        groupId: Group ID
    
    Returns:
        HTMLResponse: HTML page with results visualization
    """
    context = check_group_expiration(groupId)
    group = context["group"]
    db = context["db"]
    
    try:
        from src.models.free_time_result import FreeTimeResult
        from src.models.submission import Submission
        from fastapi.responses import HTMLResponse
        
        # Get latest result
        result = db.query(FreeTimeResult).filter(
            FreeTimeResult.group_id == groupId
        ).order_by(FreeTimeResult.version.desc()).first()
        
        # Get participants
        participants = db.query(Submission).filter(
            Submission.group_id == groupId,
            Submission.status == "success"
        ).all()
        
        # Build response data
        response_data = {
            "group_id": str(group.id),
            "group_name": group.group_name,
            "participant_count": len(participants),
            "participants": [
                {
                    "nickname": p.nickname,
                    "submitted_at": p.created_at.isoformat() + "Z"
                }
                for p in sorted(participants, key=lambda p: p.created_at)
            ],
            "free_time": result.free_time_intervals if result else [],
            "availability_by_day": result.availability_by_day if result else {},
            "computed_at": result.computed_at.isoformat() + "Z" if result else None,
            "expires_at": group.expires_at.isoformat() + "Z",
            "display_unit_minutes": group.display_unit_minutes,
            "version": result.version if result else 0
        }
        
        # Render HTML
        html = render_free_time_template(response_data)
        
        return HTMLResponse(content=html, status_code=200)
    finally:
        db_manager.close_session(db)

