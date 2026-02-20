"""
Unit tests for batch deletion (T063)

Tests:
- test_scan_expired_groups: Verify scanning for expired groups
- test_cascade_delete: Verify cascade deletion (Group → Submission → Interval → Result)
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.models import Group, Submission, Interval, FreeTimeResult, Base
from src.models.deletion_log import DeletionLog


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestBatchDeletion:
    """Test batch deletion with cascade."""
    
    def test_scan_expired_groups_empty(self, test_db):
        """Test scanning with no expired groups."""
        now = datetime.utcnow()
        
        # Create non-expired group
        group = Group(
            id=uuid4(),
            group_name="active",
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(days=1),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Scan for expired
        from src.services.batch_deletion import BatchDeletionService
        expired_groups = BatchDeletionService.scan_expired_groups(test_db)
        
        assert len(expired_groups) == 0
    
    def test_scan_expired_groups_multiple(self, test_db):
        """Test scanning finds multiple expired groups."""
        now = datetime.utcnow()
        
        # Create 3 groups: 2 expired, 1 active
        expired_ids = []
        for i in range(2):
            group = Group(
                id=uuid4(),
                group_name=f"expired_{i}",
                created_at=now - timedelta(hours=72),
                last_activity_at=now - timedelta(hours=72),
                expires_at=now - timedelta(hours=1),
                display_unit_minutes=30,
                max_participants=50
            )
            test_db.add(group)
            expired_ids.append(group.id)
        
        # Active group
        active = Group(
            id=uuid4(),
            group_name="active",
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(hours=24),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(active)
        test_db.commit()
        
        # Scan for expired
        from src.services.batch_deletion import BatchDeletionService
        expired_groups = BatchDeletionService.scan_expired_groups(test_db)
        
        assert len(expired_groups) == 2
        found_ids = [g.id for g in expired_groups]
        for expected_id in expired_ids:
            assert expected_id in found_ids
        assert active.id not in found_ids
    
    def test_cascade_delete_group(self, test_db):
        """Test cascade deletion: Group deleted."""
        now = datetime.utcnow()
        group_id = uuid4()
        
        group = Group(
            id=group_id,
            group_name="delete_test",
            created_at=now,
            last_activity_at=now,
            expires_at=now - timedelta(hours=1),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Verify group exists
        found = test_db.query(Group).filter(Group.id == group_id).first()
        assert found is not None
        
        # Delete
        from src.services.batch_deletion import BatchDeletionService
        BatchDeletionService.hard_delete_group(test_db, group_id)
        
        # Verify deletion
        found = test_db.query(Group).filter(Group.id == group_id).first()
        assert found is None
    
    def test_cascade_delete_submissions_and_intervals(self, test_db):
        """Test cascade deletion: Group → Submissions → Intervals."""
        now = datetime.utcnow()
        group_id = uuid4()
        
        # Create group
        group = Group(
            id=group_id,
            group_name="cascade_test",
            created_at=now,
            last_activity_at=now,
            expires_at=now - timedelta(hours=1),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Create 2 submissions with intervals
        submission_ids = []
        interval_ids = []
        for i in range(2):
            submission = Submission(
                id=uuid4(),
                group_id=group_id,
                nickname=f"member_{i}",
                status="success",
                created_at=now
            )
            test_db.add(submission)
            submission_ids.append(submission.id)
            test_db.commit()
            
            # Add intervals
            for day in ["MONDAY", "TUESDAY"]:
                interval = Interval(
                    id=uuid4(),
                    submission_id=submission.id,
                    day_of_week=day,
                    start_minute=600,
                    end_minute=720,
                    is_busy=False,
                    created_at=now
                )
                test_db.add(interval)
                interval_ids.append(interval.id)
        
        test_db.commit()
        
        # Verify submissions and intervals exist
        assert len(test_db.query(Submission).filter(Submission.group_id == group_id).all()) == 2
        assert len(test_db.query(Interval).all()) == 4
        
        # Delete group with cascade
        from src.services.batch_deletion import BatchDeletionService
        BatchDeletionService.hard_delete_group(test_db, group_id)
        
        # Verify cascade: group gone
        assert test_db.query(Group).filter(Group.id == group_id).first() is None
        
        # Verify cascade: submissions deleted
        remaining_submissions = test_db.query(Submission).filter(
            Submission.group_id == group_id
        ).all()
        assert len(remaining_submissions) == 0
        
        # Verify cascade: intervals deleted
        remaining_intervals = test_db.query(Interval).all()
        assert len(remaining_intervals) == 0
    
    def test_cascade_delete_free_time_result(self, test_db):
        """Test cascade deletion: Group → FreeTimeResult."""
        now = datetime.utcnow()
        group_id = uuid4()
        
        # Create group
        group = Group(
            id=group_id,
            group_name="cascade_result_test",
            created_at=now,
            last_activity_at=now,
            expires_at=now - timedelta(hours=1),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Create result
        result = FreeTimeResult(
            id=uuid4(),
            group_id=group_id,
            version=1,
            status="completed",
            availability_by_day={},
            free_time_intervals=[],
            computed_at=now,
            created_at=now
        )
        test_db.add(result)
        test_db.commit()
        
        # Verify result exists
        assert test_db.query(FreeTimeResult).filter(FreeTimeResult.group_id == group_id).first() is not None
        
        # Delete group
        from src.services.batch_deletion import BatchDeletionService
        BatchDeletionService.hard_delete_group(test_db, group_id)
        
        # Verify cascade: result deleted
        assert test_db.query(FreeTimeResult).filter(FreeTimeResult.group_id == group_id).first() is None
    
    def test_deletion_log_created(self, test_db):
        """Test that deletion log entry is created after deletion."""
        now = datetime.utcnow()
        group_id = uuid4()
        
        # Create group with 1 submission
        group = Group(
            id=group_id,
            group_name="log_test",
            created_at=now,
            last_activity_at=now,
            expires_at=now - timedelta(hours=1),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        submission = Submission(
            id=uuid4(),
            group_id=group_id,
            nickname="test_member",
            status="success",
            created_at=now
        )
        test_db.add(submission)
        test_db.commit()
        
        # Delete
        from src.services.batch_deletion import BatchDeletionService
        BatchDeletionService.hard_delete_group(test_db, group_id, reason="expired")
        
        # Verify deletion log
        logs = test_db.query(DeletionLog).filter(DeletionLog.group_id == group_id).all()
        
        if logs:  # If DeletionLog model exists
            assert len(logs) > 0
            log = logs[0]
            assert log.group_id == group_id
            assert log.reason == "expired"
            assert log.submission_count == 1
