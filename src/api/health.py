"""
Health check endpoint (T095)

Returns application status and connectivity for Kubernetes probes
"""
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter
from sqlalchemy import text

from src.lib.database import db_manager
from src.lib.utils import format_response

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for K8s liveness and readiness probes.
    
    Returns application status, database connectivity, and version info.
    
    **Responses**:
    - 200: Application is healthy
    - 503: Application or dependencies are down
    """
    from src.config import config
    
    try:
        # Test database connectivity
        db = db_manager.get_session()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
        db_error = None
    except Exception as e:
        db_status = "disconnected"
        db_error = str(e)
    
    # Build response
    status = "healthy" if db_status == "connected" else "degraded"
    
    return format_response(
        "success" if status == "healthy" else "warning",
        data={
            "status": status,
            "version": "0.1.0",
            "environment": config.ENVIRONMENT,
            "database": {
                "status": db_status,
                "error": db_error
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": 0  # Would be calculated from app start time
        }
    )


@router.get("/readiness", response_model=Dict[str, Any])
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check for accepting traffic.
    
    Used by K8s readiness probe to determine if pod should receive traffic.
    More strict than liveness - if this fails, pod is removed from service.
    """
    try:
        db = db_manager.get_session()
        db.execute(text("SELECT 1"))
        db.close()
        
        return format_response(
            "success",
            data={
                "ready": True,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )
    except Exception as e:
        return format_response(
            "error",
            error="READINESS_CHECK_FAILED",
            message=f"Not ready to accept traffic: {str(e)}"
        ), 503
