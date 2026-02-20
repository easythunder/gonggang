"""Structured logging infrastructure with PII masking."""
import json
import logging
import re
from typing import Any, Dict

from src.config import config


class PiiMaskingFormatter(logging.Formatter):
    """Custom formatter that masks Personally Identifiable Information (PII)."""

    # Regex patterns for PII
    URL_PATTERN = re.compile(r'https?://[^\s]+')
    TOKEN_PATTERN = re.compile(r'(token|api_key|admin_token)["\']?\s*[:\=]\s*["\']?([^"\'\s,}]+)')
    IMAGE_PATH_PATTERN = re.compile(r'/uploads/[^\s]+')

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with PII masking."""
        msg = super().format(record)
        
        # Mask URLs
        msg = self.URL_PATTERN.sub('[URL_MASKED]', msg)
        
        # Mask tokens
        msg = self.TOKEN_PATTERN.sub(r'\1=[MASKED]', msg)
        
        # Mask image paths
        msg = self.IMAGE_PATH_PATTERN.sub('[IMAGE_PATH_MASKED]', msg)
        
        return msg


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in ["name", "msg", "args", "created", "filename", "funcName",
                               "levelname", "levelno", "lineno", "module", "msecs",
                               "message", "pathname", "process", "processName", "relativeCreated",
                               "thread", "threadName", "exc_info", "exc_text"]:
                    log_data[key] = str(value)

        return json.dumps(log_data)


def setup_logging() -> None:
    """Setup application logging."""
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(config.LOG_LEVEL)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler with appropriate formatter
    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.LOG_LEVEL)

    if config.ENVIRONMENT == "production":
        # JSON format in production for log aggregation
        formatter = JsonFormatter()
    else:
        # Human-readable in development
        formatter = PiiMaskingFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Suppress verbose library logs
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logging.info(f"Logging configured: level={config.LOG_LEVEL}, env={config.ENVIRONMENT}")


# Setup on import
setup_logging()
logger = logging.getLogger(__name__)
