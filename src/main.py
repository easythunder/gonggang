"""FastAPI application main entry point."""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    """Health check endpoint."""
    return format_response(
        "success",
        data={
            "status": "healthy",
            "version": "0.1.0",
            "environment": config.ENVIRONMENT,
        },
    )


@app.on_event("startup")
async def startup_event():
    """Handle startup."""
    logger.info("Application starting up")


@app.on_event("shutdown")
async def shutdown_event():
    """Handle shutdown."""
    logger.info("Application shutting down")
    db_manager.close()


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT,
        log_config=None,  # Use our custom logging
    )
