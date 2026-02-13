"""Base repository class for CRUD operations."""
import logging
from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")
logger = logging.getLogger(__name__)


class BaseRepository(Generic[T]):
    """Generic repository for CRUD operations."""

    def __init__(self, session: Session, model: Type[T]):
        """Initialize repository with session and model."""
        self.session = session
        self.model = model

    def create(self, **kwargs) -> T:
        """Create a new entity."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.flush()  # Get ID without commit
        logger.debug(f"Created {self.model.__name__}: {instance.id}")
        return instance

    def get_by_id(self, entity_id) -> Optional[T]:
        """Get entity by ID."""
        return self.session.query(self.model).filter(self.model.id == entity_id).first()

    def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """List all entities with pagination."""
        return (
            self.session.query(self.model)
            .limit(limit)
            .offset(offset)
            .all()
        )

    def update(self, entity_id, **kwargs) -> Optional[T]:
        """Update entity."""
        instance = self.get_by_id(entity_id)
        if not instance:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        self.session.flush()
        logger.debug(f"Updated {self.model.__name__}: {entity_id}")
        return instance

    def delete(self, entity_id) -> bool:
        """Delete entity."""
        instance = self.get_by_id(entity_id)
        if not instance:
            return False

        self.session.delete(instance)
        self.session.flush()
        logger.debug(f"Deleted {self.model.__name__}: {entity_id}")
        return True

    def delete_instance(self, instance: T) -> bool:
        """Delete specific instance."""
        try:
            self.session.delete(instance)
            self.session.flush()
            logger.debug(f"Deleted {self.model.__name__} instance")
            return True
        except Exception as e:
            logger.error(f"Error deleting instance: {e}")
            return False

    def commit(self) -> None:
        """Commit current transaction."""
        self.session.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        self.session.rollback()
