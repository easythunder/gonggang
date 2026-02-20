"""
Contract tests for GET /groups/{id}/free-time endpoint (T053)

Tests:
- test_poll_with_results: GET /groups/{id}/free-time with valid results
- test_poll_no_results: GET /groups/{id}/free-time with no common free time
- test_poll_expired: GET /groups/{id}/free-time for expired group (410)
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.models.models import Group, Submission, Interval, FreeTimeResult, Base


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(test_db):
    """Create FastAPI test client."""
    from src.main import app
    
    # Inject test database
    app.dependency_overrides = {}
    
    # Override get_db dependency
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()
    
    from src.database import get_db
    app.dependency_overrides[get_db] = override_get_db
    
    return TestClient(app)


class TestFreeTimeResponse:
    """Test FreeTimeResponse contract compliance."""
    
    def test_poll_with_results(self, client, test_db):
        """Test GET /groups/{id}/free-time with valid results."""
        # Setup: Create group and submissions
        group_id = uuid4()
        now = datetime.utcnow()
        
        group = Group(
            id=group_id,
            group_name="test_group",
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(hours=72),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Create submissions with intervals
        for i in range(3):
            submission = Submission(
                id=uuid4(),
                group_id=group_id,
                nickname=f"member_{i}",
                status="success",
                created_at=now
            )
            test_db.add(submission)
            test_db.commit()
            
            # Add some intervals (Monday 10:00-11:00)
            interval = Interval(
                id=uuid4(),
                submission_id=submission.id,
                day_of_week="MONDAY",
                start_minute=600,  # 10:00
                end_minute=660,    # 11:00
                is_busy=False,
                created_at=now
            )
            test_db.add(interval)
        
        # Create free time result
        result = FreeTimeResult(
            id=uuid4(),
            group_id=group_id,
            version=1,
            status="completed",
            availability_by_day={
                "MONDAY": [
                    {
                        "slot_id": "MON_10_00",
                        "start_minute": 600,
                        "end_minute": 660,
                        "availability_count": 3,
                        "is_common": True
                    }
                ]
            },
            free_time_intervals=[
                {
                    "day": "MONDAY",
                    "start_minute": 600,
                    "end_minute": 660,
                    "duration_minutes": 60,
                    "overlap_count": 3
                }
            ],
            computed_at=now,
            created_at=now
        )
        test_db.add(result)
        test_db.commit()
        
        # Execute: GET /groups/{id}/free-time
        response = client.get(f"/groups/{group_id}/free-time")
        
        # Assert: 200 OK
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["group_id"] == str(group_id)
        assert data["group_name"] == "test_group"
        assert data["participant_count"] == 3
        assert "free_time" in data
        assert len(data["free_time"]) > 0
        assert data["free_time"][0]["day"] == "MONDAY"
        assert data["free_time"][0]["start_minute"] == 600
        assert data["free_time"][0]["duration_minutes"] == 60
        assert data["free_time"][0]["overlap_count"] == 3
        assert "computed_at" in data
        assert "expires_at" in data
        assert data["display_unit_minutes"] == 30
        assert "participants" in data
        assert len(data["participants"]) == 3
        
        # Verify response headers
        assert "X-Poll-Wait" in response.headers
        poll_wait = int(response.headers["X-Poll-Wait"])
        assert 2000 <= poll_wait <= 3000
        
        assert "X-Response-Time" in response.headers
        assert "X-Calculation-Version" in response.headers
        assert response.headers["X-Calculation-Version"] == "1"
    
    def test_poll_no_results(self, client, test_db):
        """Test GET /groups/{id}/free-time with no common free time."""
        group_id = uuid4()
        now = datetime.utcnow()
        
        group = Group(
            id=group_id,
            group_name="conflict_group",
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(hours=72),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Create 2 submissions with conflicting schedules
        for i in range(2):
            submission = Submission(
                id=uuid4(),
                group_id=group_id,
                nickname=f"busy_{i}",
                status="success",
                created_at=now
            )
            test_db.add(submission)
            test_db.commit()
            
            # Each busy on different times (no overlap)
            if i == 0:
                start, end = 600, 660  # 10:00-11:00
            else:
                start, end = 1200, 1260  # 20:00-21:00
            
            interval = Interval(
                id=uuid4(),
                submission_id=submission.id,
                day_of_week="MONDAY",
                start_minute=start,
                end_minute=end,
                is_busy=False,
                created_at=now
            )
            test_db.add(interval)
        
        # Create result with no free time
        result = FreeTimeResult(
            id=uuid4(),
            group_id=group_id,
            version=1,
            status="completed",
            availability_by_day={"MONDAY": []},
            free_time_intervals=[],
            computed_at=now,
            created_at=now
        )
        test_db.add(result)
        test_db.commit()
        
        # Execute
        response = client.get(f"/groups/{group_id}/free-time")
        
        # Assert: 200 OK with empty free_time
        assert response.status_code == 200
        data = response.json()
        assert data["participant_count"] == 2
        assert data["free_time"] == []
        assert len(data["participants"]) == 2
    
    def test_poll_expired(self, client, test_db):
        """Test GET /groups/{id}/free-time for expired group (410)."""
        group_id = uuid4()
        now = datetime.utcnow()
        
        # Create expired group
        group = Group(
            id=group_id,
            group_name="expired_group",
            created_at=now - timedelta(hours=73),
            last_activity_at=now - timedelta(hours=73),
            expires_at=now - timedelta(hours=1),  # Already expired
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Execute
        response = client.get(f"/groups/{group_id}/free-time")
        
        # Assert: 410 Gone
        assert response.status_code == 410
        data = response.json()
        assert "error" in data
        assert data["error"] == "group_expired"
        assert "message" in data


class TestParticipantList:
    """Test participants field in FreeTimeResponse."""
    
    def test_participants_included(self, client, test_db):
        """Test that participants list is included with nicknames."""
        group_id = uuid4()
        now = datetime.utcnow()
        
        group = Group(
            id=group_id,
            group_name="group_with_members",
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(hours=72),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Create 3 submissions
        nicknames = ["happy_blue_lion", "swift_silver_mountain", "joy_green_river"]
        submission_times = []
        for i, nickname in enumerate(nicknames):
            sub_time = now - timedelta(minutes=i*10)
            submission = Submission(
                id=uuid4(),
                group_id=group_id,
                nickname=nickname,
                status="success",
                created_at=sub_time
            )
            test_db.add(submission)
            submission_times.append(sub_time)
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
        
        # Execute
        response = client.get(f"/groups/{group_id}/free-time")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "participants" in data
        assert len(data["participants"]) == 3
        
        # Check all nicknames are present
        returned_nicknames = [p["nickname"] for p in data["participants"]]
        for nickname in nicknames:
            assert nickname in returned_nicknames
        
        # Check submitted_at is present for each
        for participant in data["participants"]:
            assert "submitted_at" in participant
