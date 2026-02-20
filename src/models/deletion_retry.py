"""
Deletion retry tracking model (T064)

Tracks failed deletion attempts with exponential backoff.
"""
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.models.models import Base


class DeletionRetry(Base):
    """Track deletion retry attempts with exponential backoff."""
    
    __tablename__ = "deletion_retries"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    group_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True, unique=True)
    failure_count = Column(Integer, default=1)
    last_failed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<DeletionRetry {self.group_id} failures={self.failure_count}>"
