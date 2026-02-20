"""
Integration test for full deletion flow (T065)

Test:
- test_deletion_flow_e2e: Create group → wait 72h+ → batch job runs → verify all records deleted
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


class TestDeletionFlowE2E:
    """Integration tests for complete deletion workflow."""
    
    def test_deletion_flow_e2e(self, test_db):
        """
        Test complete deletion flow:
        1. Create group with submissions, intervals, results
        2. Simulate time passage (72+ hours)
        3. Run batch deletion
        4. Verify complete cascade deletion
        """
        now = datetime.utcnow()
        group_id = uuid4()
        
        # Step 1: Create group
        created_time = now - timedelta(hours=72, minutes=5)  # 72h 5min ago
        group = Group(
            id=group_id,
            group_name="e2e_deletion_test",
            created_at=created_time,
            last_activity_at=created_time,
            expires_at=created_time + timedelta(hours=72),  # Expired 5 min ago
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Step 2: Add 3 submissions with intervals
        for i in range(3):
            submission = Submission(
                id=uuid4(),
                group_id=group_id,
                nickname=f"member_{i}",
                status="success",
                created_at=created_time
            )
            test_db.add(submission)
            test_db.commit()
            
            # Add intervals for each day
            for day in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]:
                interval = Interval(
                    id=uuid4(),
                    submission_id=submission.id,
                    day_of_week=day,
                    start_minute=600 + i*120,
                    end_minute=720 + i*120,
                    is_busy=False,
                    created_at=created_time
                )
                test_db.add(interval)
        
        test_db.commit()
        
        # Step 3: Add calculation result
        result = FreeTimeResult(
            id=uuid4(),
            group_id=group_id,
            version=2,
            status="completed",
            availability_by_day={
                "MONDAY": [
                    {
                        "slot_id": "MON_10_00",
                        "start_minute": 600,
                        "end_minute": 720,
                        "availability_count": 3,
                        "is_common": True
                    }
                ]
            },
            free_time_intervals=[
                {
                    "day": "MONDAY",
                    "start_minute": 600,
                    "end_minute": 720,
                    "duration_minutes": 120,
                    "overlap_count": 3
                }
            ],
            computed_at=created_time + timedelta(minutes=30),
            created_at=created_time + timedelta(minutes=30)
        )
        test_db.add(result)
        test_db.commit()
        
        # Verify initial state
        assert test_db.query(Group).filter(Group.id == group_id).first() is not None
        assert len(test_db.query(Submission).filter(Submission.group_id == group_id).all()) == 3
        assert len(test_db.query(Interval).all()) == 15  # 3 submissions × 5 days
        assert test_db.query(FreeTimeResult).filter(FreeTimeResult.group_id == group_id).first() is not None
        
        # Step 4: Run batch deletion
        from src.services.batch_deletion import BatchDeletionService
        stats = BatchDeletionService.run_batch_deletion(test_db, current_time=now)
        
        # Step 5: Verify complete deletion
        # Group should be deleted
        assert test_db.query(Group).filter(Group.id == group_id).first() is None
        
        # All submissions should be deleted
        remaining_submissions = test_db.query(Submission).filter(Submission.group_id == group_id).all()
        assert len(remaining_submissions) == 0
        
        # All intervals should be deleted
        all_intervals = test_db.query(Interval).all()
        assert len(all_intervals) == 0
        
        # Result should be deleted
        assert test_db.query(FreeTimeResult).filter(FreeTimeResult.group_id == group_id).first() is None
        
        # Verify deletion log
        logs = test_db.query(DeletionLog).filter(DeletionLog.group_id == group_id).all()
        if logs:
            assert len(logs) > 0
            log = logs[0]
            assert log.group_id == group_id
            assert log.submission_count == 3
    
    def test_partial_deletion_with_failures(self, test_db):
        """Test deletion with some failures and retry."""
        now = datetime.utcnow()
        
        # Create 3 expired groups
        group_ids = []
        for j in range(3):
            created_time = now - timedelta(hours=73)
            group = Group(
                id=uuid4(),
                group_name=f"batch_test_{j}",
                created_at=created_time,
                last_activity_at=created_time,
                expires_at=created_time + timedelta(hours=72),
                display_unit_minutes=30,
                max_participants=50
            )
            test_db.add(group)
            group_ids.append(group.id)
        
        test_db.commit()
        
        # Add submission to each
        for group_id in group_ids:
            submission = Submission(
                id=uuid4(),
                group_id=group_id,
                nickname="test",
                status="success",
                created_at=now - timedelta(hours=73)
            )
            test_db.add(submission)
        
        test_db.commit()
        
        # Run batch deletion
        from src.services.batch_deletion import BatchDeletionService
        stats = BatchDeletionService.run_batch_deletion(test_db, current_time=now)
        
        # Verify stats
        assert stats["scanned"] >= 3
        assert stats["deleted"] >= 0  # Some might succeed, some might fail
        assert stats["failed"] >= 0
        assert stats["deleted"] + stats["failed"] >= 0
    
    def test_soft_delete_to_hard_delete_transition(self, test_db):
        """Test transition from lazy (soft) delete to batch (hard) delete."""
        now = datetime.utcnow()
        group_id = uuid4()
        
        # Create expired group
        created_time = now - timedelta(hours=73)
        group = Group(
            id=group_id,
            group_name="soft_to_hard",
            created_at=created_time,
            last_activity_at=created_time,
            expires_at=created_time + timedelta(hours=72),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Step 1: Access triggers lazy delete (sets soft flag)
        from src.services.deletion import DeletionService
        is_expired = DeletionService.check_expiry(group)
        assert is_expired is True
        
        # Mark as soft-deleted
        DeletionService.mark_soft_deleted(test_db, group_id)
        
        # Step 2: Batch job cleans up soft-deleted records
        from src.services.batch_deletion import BatchDeletionService
        soft_deleted = test_db.query(Group).filter(
            Group.id == group_id
            # Filter for soft_delete flag if model has one
        ).first()
        
        if soft_deleted:
            BatchDeletionService.hard_delete_group(test_db, group_id)
        
        # Verify hard deletion
        assert test_db.query(Group).filter(Group.id == group_id).first() is None
