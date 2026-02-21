"""Schedule analysis API endpoints.

분석 엔드포인트:
- GET /analysis/groups/{group_id}/overlaps: 공통 자유 시간 분석
"""

import logging
from uuid import UUID
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

from src.lib.database import db_manager
from src.services.schedule_analyzer import TimeOverlapAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


# Response schemas
class TimeSlotInfo(BaseModel):
    """시간 슬롯 정보"""
    day: int = Field(..., description="Day of week (0-6, Monday-Sunday)")
    day_name: str = Field(..., description="Korean day name")
    start_time: str = Field(..., description="Start time HH:MM")
    end_time: str = Field(..., description="End time HH:MM")
    start_minute: int = Field(..., description="Start minutes from midnight")
    end_minute: int = Field(..., description="End minutes from midnight")
    duration_minutes: int = Field(..., description="Duration in minutes")


class OverlapInfo(BaseModel):
    """두 사람 간의 시간 겹침"""
    person1: str = Field(..., description="First person's nickname")
    person2: str = Field(..., description="Second person's nickname")
    count: int = Field(..., description="Number of overlapping slots")


class FreeTimeInfo(BaseModel):
    """자유 시간 정보"""
    day: int = Field(..., description="Day of week")
    day_name: str = Field(..., description="Korean day name")
    start_time: str = Field(..., description="Start time HH:MM")
    end_time: str = Field(..., description="End time HH:MM")
    duration_minutes: int = Field(..., description="Duration in minutes")


class OverlapAnalysisResponse(BaseModel):
    """시간 겹침 분석 응답"""
    group_id: str = Field(..., description="Group UUID")
    participant_count: int = Field(..., description="Number of successful participants")
    participants: List[str] = Field(..., description="List of participant nicknames")
    total_overlapping_slots: int = Field(..., description="Total overlapping time slots found")
    total_free_minutes: int = Field(..., description="Total common free time in minutes")
    free_times_count: int = Field(..., description="Number of free time slots >= 60min")
    summary: str = Field(..., description="Human-readable summary")


@router.get("/groups/{group_id}/overlaps", response_model=OverlapAnalysisResponse)
async def analyze_group_overlaps(group_id: str) -> OverlapAnalysisResponse:
    """
    분석: 그룹의 모든 참가자의 시간 겹침과 공통 자유 시간을 분석합니다.
    
    Logic:
    1. 그룹의 모든 성공한 submission을 로드
    2. 각 submission의 intervals을 읽음
    3. 시간 겹침 분석 (모든 쌍의 교집합)
    4. 공통 자유 시간 계산 (모든 사람이 자유로운 시간)
    
    Args:
        group_id: Group UUID
    
    Returns:
        분석 결과 with summary
    """
    db = db_manager.get_session()
    
    try:
        # Validate UUID format
        try:
            group_uuid = UUID(group_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid group_id format")
        
        # Check if group has submissions with raw SQL
        from sqlalchemy import text
        result = db.execute(
            text("""
                SELECT COUNT(*) as count FROM submissions 
                WHERE group_id = :group_id::uuid AND status = 'success'
            """),
            {"group_id": str(group_uuid)}
        )
        count = result.scalar()
        
        if not count or count == 0:
            raise HTTPException(status_code=404, detail="Group not found or no submissions")
        
        # Analyze overlaps
        analyzer = TimeOverlapAnalyzer(db)
        analysis = analyzer.analyze_group_overlaps(group_uuid)
        
        # Calculate statistics
        total_overlapping = sum(
            len(overlap['overlapping_times'])
            for overlap in analysis['overlaps']
        )
        
        total_free_minutes = sum(
            end - start
            for day_slots in analysis['free_times'].values()
            for start, end in day_slots
        )
        
        free_times_count = sum(
            len(day_slots)
            for day_slots in analysis['free_times'].values()
        )
        
        # Generate human-readable summary
        summary = analyzer.get_human_readable_report(analysis)
        
        # Get nicknames
        nicknames = [p['nickname'] for p in analysis['participants']]
        
        response = OverlapAnalysisResponse(
            group_id=str(group_uuid),
            participant_count=analysis['participant_count'],
            participants=nicknames,
            total_overlapping_slots=total_overlapping,
            total_free_minutes=total_free_minutes,
            free_times_count=free_times_count,
            summary=summary
        )
        
        logger.info(
            f"Analysis complete for group {group_uuid}: "
            f"{analysis['participant_count']} participants, "
            f"{total_free_minutes}min common free time"
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed for group {group_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Analysis failed")
    finally:
        db.close()


@router.get("/groups/{group_id}/overlaps/summary")
async def get_overlap_summary(group_id: str):
    """
    빠른 요약만 반환 (plain text).
    
    Args:
        group_id: Group UUID
    
    Returns:
        Human-readable summary text
    """
    db = db_manager.get_session()
    
    try:
        try:
            group_uuid = UUID(group_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid group_id format")
        
        # Use raw SQL to avoid model loading  issues
        from sqlalchemy import text
        
        # Check if group exists with submissions
        result = db.execute(
            text("""
                SELECT COUNT(*) as count FROM submissions 
                WHERE group_id = :group_id::uuid AND status = 'success'
            """),
            {"group_id": str(group_uuid)}
        )
        count = result.scalar()
        
        if not count or count == 0:
            raise HTTPException(status_code=404, detail="Group not found or no submissions")
        
        analyzer = TimeOverlapAnalyzer(db)
        analysis = analyzer.analyze_group_overlaps(group_uuid)
        summary = analyzer.get_human_readable_report(analysis)
        
        # Return as plain text
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(content=summary)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summary generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Summary generation failed")
    finally:
        db.close()
