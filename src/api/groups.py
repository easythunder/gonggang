"""Group API endpoints."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Response, status
from pydantic import BaseModel, Field

from src.lib.database import db_manager
from src.services.group import GroupService
from src.lib.utils import ErrorCodes, format_response, validate_display_unit
from src.config import config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groups", tags=["groups"])


# Request/Response models
class CreateGroupRequest(BaseModel):
    """Request model for creating a group."""

    group_name: Optional[str] = Field(None, max_length=255)
    display_unit_minutes: int = Field(30, description="10, 20, 30, or 60")


class GroupResponse(BaseModel):
    """Response model for group details."""

    group_id: str
    group_name: str
    created_at: str
    expires_at: str
    invite_url: str
    share_url: str
    display_unit_minutes: int
    max_participants: int


class GroupStatsResponse(BaseModel):
    """Response model for group statistics."""

    group_id: str
    name: str
    total_submissions: int
    successful_submissions: int
    total_intervals: int
    display_unit_minutes: int
    created_at: str
    last_activity_at: str
    expires_at: str
    time_remaining_hours: float


def get_group_service():
    """Dependency: Get group service with database session."""
    session = db_manager.get_session()
    try:
        yield GroupService(session)
    finally:
        session.close()


@router.post(
    "",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new group",
)
async def create_group(
    request: CreateGroupRequest,
    service: GroupService = Depends(get_group_service),
):
    """Create a new group for schedule coordination.
    
    - **group_name** (optional): Custom name for the group. Auto-generated if not provided.
    - **display_unit_minutes** (required): Display granularity (10, 20, 30, or 60 minutes)
    
    Returns invite and share URLs for the group.
    """
    # Validate display unit
    if not validate_display_unit(request.display_unit_minutes):
        logger.warning(
            f"Invalid display unit: {request.display_unit_minutes}",
            extra={"endpoint": "create_group"}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": ErrorCodes.INVALID_DISPLAY_UNIT,
                "message": f"display_unit_minutes must be one of {config.DISPLAY_UNIT_OPTIONS}",
            }
        )

    # Create group
    group, error = service.create_group(
        group_name=request.group_name,
        display_unit_minutes=request.display_unit_minutes,
    )

    if error:
        logger.error(f"Failed to create group: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": error,
                "message": "Failed to create group",
            }
        )

    # Return response
    return format_response(
        "success",
        data={
            "group_id": str(group.id),
            "group_name": group.name,
            "created_at": group.created_at.isoformat(),
            "expires_at": group.expires_at.isoformat(),
            "invite_url": group.invite_url,
            "share_url": group.share_url,
            "display_unit_minutes": group.display_unit_minutes,
            "max_participants": group.max_participants,
        },
        message="Group created successfully",
    )


@router.get(
    "/{group_id}",
    response_model=dict,
    summary="Get group details",
)
async def get_group(
    group_id: str,
    service: GroupService = Depends(get_group_service),
):
    """Get group details including URLs and expiration info.
    
    Returns 410 Gone if the group has expired.
    """
    import uuid
    
    # Validate UUID
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": ErrorCodes.BAD_REQUEST,
                "message": "Invalid group ID format",
            }
        )

    # Get group
    group, error = service.get_group(group_uuid)

    if error == ErrorCodes.GROUP_EXPIRED:
        logger.info(f"Accessing expired group: {group_id}")
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "error": ErrorCodes.GROUP_EXPIRED,
                "message": "This group has expired and is no longer available",
            }
        )

    if error or not group:
        logger.warning(f"Group not found: {group_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": ErrorCodes.GROUP_NOT_FOUND,
                "message": "Group not found",
            }
        )

    # Return response
    return format_response(
        "success",
        data={
            "group_id": str(group.id),
            "group_name": group.name,
            "created_at": group.created_at.isoformat(),
            "expires_at": group.expires_at.isoformat(),
            "invite_url": group.invite_url,
            "share_url": group.share_url,
            "display_unit_minutes": group.display_unit_minutes,
            "max_participants": group.max_participants,
        },
    )


@router.get(
    "/{group_id}/stats",
    response_model=dict,
    summary="Get group statistics",
)
async def get_group_stats(
    group_id: str,
    service: GroupService = Depends(get_group_service),
):
    """Get group statistics (submission count, intervals, etc)."""
    import uuid
    
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": ErrorCodes.BAD_REQUEST},
        )

    # Check expiration first
    if service.check_expiry(group_uuid):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"error": ErrorCodes.GROUP_EXPIRED},
        )

    # Get stats
    stats = service.get_group_stats(group_uuid)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": ErrorCodes.GROUP_NOT_FOUND},
        )

    return format_response("success", data=stats)
