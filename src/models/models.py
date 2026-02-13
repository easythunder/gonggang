"""SQLAlchemy models for Meet-Match."""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum as py_enum

Base = declarative_base()


class SubmissionStatus(str, py_enum.Enum):
    """Submission status enumeration."""

    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class Group(Base):
    """Group data model."""

    __tablename__ = "groups"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name = Column(String(255), nullable=False, unique=True)
    display_unit_minutes = Column(Integer, nullable=False)  # 10, 20, 30, 60
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_activity_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    admin_token = Column(String(255), nullable=False, unique=True)
    invite_url = Column(String(500), nullable=False, unique=True)
    share_url = Column(String(500), nullable=False, unique=True)
    max_participants = Column(Integer, nullable=False, default=50)

    # Relationships
    submissions: List["Submission"] = relationship(
        "Submission",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    free_time_result: Optional["FreeTimeResult"] = relationship(
        "FreeTimeResult",
        back_populates="group",
        uselist=False,
        cascade="all, delete-orphan",
    )
    deletion_logs: List["DeletionLog"] = relationship(
        "DeletionLog",
        back_populates="group",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Group {self.id} name={self.name}>"

    def is_expired(self) -> bool:
        """Check if group has expired."""
        return datetime.utcnow() >= self.expires_at


class Submission(Base):
    """Participant submission data model."""

    __tablename__ = "submissions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nickname = Column(String(255), nullable=False)
    submitted_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    status = Column(
        Enum(SubmissionStatus),
        nullable=False,
        default=SubmissionStatus.PENDING,
    )
    error_reason = Column(String(500), nullable=True)

    # Relationships
    group: Group = relationship("Group", back_populates="submissions")
    intervals: List["Interval"] = relationship(
        "Interval",
        back_populates="submission",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Unique constraint: group + nickname combination
        ("group_id", "nickname"),
    )

    def __repr__(self) -> str:
        return f"<Submission {self.id} nickname={self.nickname}>"


class Interval(Base):
    """Time interval for a submission (5-min slot based)."""

    __tablename__ = "intervals"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    submission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week = Column(Integer, nullable=False)  # 0-6 (Monday-Sunday)
    start_minute = Column(Integer, nullable=False)  # 0-1439 (5-min aligned)
    end_minute = Column(Integer, nullable=False)  # 0-1439 (5-min aligned)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    submission: Submission = relationship("Submission", back_populates="intervals")

    __table_args__ = (
        # Index for efficient lookups by day
        ("day_of_week", "start_minute"),
    )

    def __repr__(self) -> str:
        return (
            f"<Interval {self.id} day={self.day_of_week} "
            f"start={self.start_minute} end={self.end_minute}>"
        )


class FreeTimeResult(Base):
    """Calculated free time results for a group."""

    __tablename__ = "group_free_time_results"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    version = Column(Integer, nullable=False, default=1)
    availability_by_day = Column(JSON, nullable=True)  # JSONB: grid structure
    free_time_intervals = Column(JSON, nullable=True)  # JSONB: candidate list
    computed_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    status = Column(
        Enum(SubmissionStatus),
        nullable=False,
        default=SubmissionStatus.PENDING,
    )
    error_code = Column(String(100), nullable=True)

    # Relationships
    group: Group = relationship("Group", back_populates="free_time_result")

    def __repr__(self) -> str:
        return f"<FreeTimeResult {self.id} group={self.group_id} v{self.version}>"


class DeletionLog(Base):
    """Audit log for deletions."""

    __tablename__ = "deletion_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    group_id = Column(
        UUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    reason = Column(String(100), nullable=False)  # 'expired', 'manual', 'batch_failure'
    submission_count = Column(Integer, nullable=True)
    asset_count = Column(Integer, nullable=True)
    error_code = Column(String(100), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # Relationships
    group: Optional[Group] = relationship("Group", back_populates="deletion_logs")

    def __repr__(self) -> str:
        return f"<DeletionLog {self.id} group={self.group_id} reason={self.reason}>"
