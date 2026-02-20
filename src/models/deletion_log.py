"""
Deletion audit log model (T070)

Records all deletions for audit and monitoring purposes.
"""
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.models.models import Base


class DeletionLog(Base):
    """Audit log for group deletions."""
    
    __tablename__ = "deletion_logs"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    group_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    reason = Column(String(50), nullable=False)  # 'expired', 'manual', 'error_cleanup'
    submission_count = Column(Integer, default=0)
    interval_count = Column(Integer, default=0)
    asset_count = Column(Integer, default=0)
    error_code = Column(String(100), nullable=True)
    retry_count = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<DeletionLog {self.group_id} reason={self.reason} at={self.deleted_at}>"
