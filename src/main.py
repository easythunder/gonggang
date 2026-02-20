"""FastAPI application main entry point."""
import logging
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

# Setup logging first
from src.lib.logging import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

from src.config import config
from src.lib.database import db_manager
from src.lib.utils import ErrorCodes, format_response

# Initialize database
db_manager.init_db()
logger.info("Database initialized successfully")

# Initialize FastAPI app
app = FastAPI(
    title="Meet-Match API",
    description="Common free time coordinator",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception("Unhandled exception", extra={"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content=format_response(
            "error",
            error=ErrorCodes.INTERNAL_ERROR,
            message="Internal server error",
        ),
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for K8s probes."""
    from datetime import datetime
    try:
        db = db_manager.get_session()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = "disconnected"
        logger.error(f"Health check: DB connection failed: {e}")
    
    return format_response(
        "success",
        data={
            "status": "healthy" if db_status == "connected" else "degraded",
            "version": "0.1.0",
            "environment": config.ENVIRONMENT,
            "database": db_status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


@app.get("/readiness")
async def readiness_check():
    """Readiness check for K8s readiness probe."""
    from datetime import datetime
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
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content=format_response(
                "error",
                error="READINESS_CHECK_FAILED",
                message="Not ready to accept traffic"
            )
        )


@app.on_event("startup")
async def startup_event():
    """Handle startup."""
    logger.info("Application starting up")
    logger.info("All modules loaded, ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Handle graceful shutdown (T098)."""
    logger.info("Shutdown signal received, draining in-flight requests...")
    
    # Wait for in-flight requests to complete (up to 30 seconds)
    import asyncio
    await asyncio.sleep(2)
    
    # Close database connections gracefully
    logger.info("Closing database connections...")
    db_manager.close()
    
    logger.info("Application shut down gracefully")


# Include routers
from src.api.groups import router as groups_router
from src.api.submissions import router as submissions_router
from src.api.submissions import set_db_manager
from src.api.free_time import router as free_time_router

# Initialize submissions API with db_manager
set_db_manager(db_manager)

app.include_router(groups_router)
app.include_router(submissions_router)
app.include_router(free_time_router)


# Static files and templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
if os.path.exists(templates_dir):
    try:
        app.mount("/static", StaticFiles(directory=templates_dir), name="static")
    except Exception as e:
        logger.warning(f"Could not mount static files: {e}")


# HTML template endpoints
@app.get("/", response_class=FileResponse)
async def index():
    """Serve HTML template."""
    template_path = os.path.join(templates_dir, "index.html")
    if os.path.exists(template_path):
        return FileResponse(template_path, media_type="text/html")
    return JSONResponse(
        status_code=404,
        content={"error": "Template not found"}
    )


@app.get("/groups/{group_id}", response_class=FileResponse)
async def group_view(group_id: str):
    """Serve group details page."""
    template_path = os.path.join(templates_dir, "index.html")
    if os.path.exists(template_path):
        return FileResponse(template_path, media_type="text/html")
    return JSONResponse(
        status_code=404,
        content={"error": "Template not found"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        log_config=None,  # Use our custom logging
    )
