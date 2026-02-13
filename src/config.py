"""Environment configuration management."""
import os
from typing import Optional


class Config:
    """Configuration for Meet-Match application."""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://gonggang:gonggang_dev_password@localhost:5432/gonggang"
    )

    # Application
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")

    # OCR
    OCR_LIBRARY: str = os.getenv("OCR_LIBRARY", "tesseract")  # tesseract or paddleocr
    OCR_TIMEOUT_SECONDS: int = int(os.getenv("OCR_TIMEOUT_SECONDS", "3"))

    # Polling
    POLLING_INTERVAL_MIN_MS: int = 2000  # 2 seconds minimum
    POLLING_INTERVAL_MAX_MS: int = 3000  # 3 seconds maximum

    # Deletion
    DELETION_BATCH_INTERVAL_SECONDS: int = int(
        os.getenv("DELETION_BATCH_INTERVAL_SECONDS", "300")  # 5 minutes
    )
    DELETION_RETENTION_HOURS: int = 72

    # Slots
    SLOT_SIZE_MINUTES: int = 5  # Internal slot granularity
    DISPLAY_UNIT_OPTIONS: list = [10, 20, 30, 60]  # Minutes, user-selectable

    # Participants
    MAX_PARTICIPANTS_PER_GROUP: int = 50

    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))


config = Config()
