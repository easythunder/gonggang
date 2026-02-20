"""Database connection management."""
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, pool
from sqlalchemy.orm import Session, sessionmaker

from src.config import config

logger = logging.getLogger(__name__)


def get_base():
    """Lazy import of Base to avoid circular imports."""
    from src.models.models import Base
    return Base


class DatabaseManager:
    """Manages database connections and sessions."""

    _engine = None
    _session_factory = None

    @classmethod
    def init_db(cls) -> None:
        """Initialize database engine and session factory."""
        if cls._engine is not None:
            logger.warning("Database already initialized")
            return

        # Create engine with connection pooling
        cls._engine = create_engine(
            config.DATABASE_URL,
            poolclass=pool.QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Verify connections before using
            echo=config.DEBUG,  # Log SQL in debug mode
        )

        # Create session factory
        cls._session_factory = sessionmaker(
            bind=cls._engine,
            expire_on_commit=False,
        )

        # Create tables if needed
        Base = get_base()
        Base.metadata.create_all(cls._engine)
        logger.info("Database initialized: %s", config.DATABASE_URL)

    @classmethod
    def get_session(cls) -> Session:
        """Get a new database session."""
        if cls._session_factory is None:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return cls._session_factory()

    @classmethod
    @contextmanager
    def session_scope(cls) -> Generator[Session, None, None]:
        """Context manager for database sessions."""
        session = cls.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @classmethod
    def close(cls) -> None:
        """Close database connections."""
        if cls._engine:
            cls._engine.dispose()
            logger.info("Database connections closed")


# Global instance
db_manager = DatabaseManager()
