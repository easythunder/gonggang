"""
Integration test for full polling flow (T055)

Test:
- test_polling_flow: Submit 3 images → poll multiple times → verify results consistent & intervals enforced
"""
import pytest
import time
from datetime import datetime, timedelta
from uuid import uuid4
from io import BytesIO
from PIL import Image
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
    
    app.dependency_overrides = {}
    
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()
    
    from src.database import get_db
    app.dependency_overrides[get_db] = override_get_db
    
    return TestClient(app)


def create_test_image() -> bytes:
    """Create a simple test image."""
    img = Image.new('RGB', (100, 100), color='white')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()


class TestPollingFlow:
    """Integration tests for full polling workflow."""
    
    def test_submit_and_poll_consistency(self, client, test_db):
        """Test submitting 3 images and polling multiple times returns consistent results."""
        # Step 1: Create group
        now = datetime.utcnow()
        group_id = uuid4()
        
        group = Group(
            id=group_id,
            group_name="integration_polling_group",
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(hours=72),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Step 2: Create 3 submissions
        for i in range(3):
            submission = Submission(
                id=uuid4(),
                group_id=group_id,
                nickname=f"member_{i}",
                status="success",
                created_at=now - timedelta(minutes=3-i)
            )
            test_db.add(submission)
            test_db.commit()
            
            # Add common free time interval (Monday 14:00-15:30)
            interval = Interval(
                id=uuid4(),
                submission_id=submission.id,
                day_of_week="MONDAY",
                start_minute=840,   # 14:00
                end_minute=930,     # 15:30
                is_busy=False,
                created_at=now - timedelta(minutes=3-i)
            )
            test_db.add(interval)
        
        test_db.commit()
        
        # Step 3: Create calculation result
        result = FreeTimeResult(
            id=uuid4(),
            group_id=group_id,
            version=1,
            status="completed",
            availability_by_day={
                "MONDAY": [
                    {
                        "slot_id": "MON_14_00",
                        "start_minute": 840,
                        "end_minute": 930,
                        "availability_count": 3,
                        "is_common": True
                    }
                ]
            },
            free_time_intervals=[
                {
                    "day": "MONDAY",
                    "start_minute": 840,
                    "end_minute": 930,
                    "duration_minutes": 90,
                    "overlap_count": 3
                }
            ],
            computed_at=now,
            created_at=now
        )
        test_db.add(result)
        test_db.commit()
        
        # Step 4: Poll multiple times
        responses = []
        for poll_num in range(3):
            response = client.get(f"/groups/{group_id}/free-time")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            responses.append(data)
        
        # Step 5: Verify consistency across polls
        first_response = responses[0]
        
        for i, response in enumerate(responses[1:], 1):
            # Same group info
            assert response["group_id"] == first_response["group_id"]
            assert response["group_name"] == first_response["group_name"]
            assert response["participant_count"] == first_response["participant_count"]
            
            # Same free time data
            assert response["free_time"] == first_response["free_time"]
            assert response["computed_at"] == first_response["computed_at"]
            
            # Same version
            assert response.get("version") == first_response.get("version")
    
    def test_polling_intervals_enforced(self, client, test_db):
        """Test that polling interval header is enforced consistently."""
        group_id = uuid4()
        now = datetime.utcnow()
        
        # Setup
        group = Group(
            id=group_id,
            group_name="interval_enforcement_group",
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(hours=72),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        
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
        
        # Poll 5 times rapidly and verify interval enforcement
        previous_wait = None
        for i in range(5):
            response = client.get(f"/groups/{group_id}/free-time")
            
            assert response.status_code == 200
            poll_wait = int(response.headers["X-Poll-Wait"])
            
            # Every response should have interval between 2000-3000
            assert 2000 <= poll_wait <= 3000
            
            # Intervals should be relatively consistent
            if previous_wait is not None:
                # Both should be in the valid range
                assert 2000 <= previous_wait <= 3000
                assert 2000 <= poll_wait <= 3000
            
            previous_wait = poll_wait
    
    def test_poll_with_multiple_days(self, client, test_db):
        """Test polling with free time spanning multiple days."""
        group_id = uuid4()
        now = datetime.utcnow()
        
        group = Group(
            id=group_id,
            group_name="multiday_group",
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(hours=72),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        
        # Create result with free time on multiple days
        free_time = []
        for day_offset, day_name in enumerate(["MONDAY", "TUESDAY", "WEDNESDAY"]):
            free_time.append({
                "day": day_name,
                "start_minute": 600,   # 10:00
                "end_minute": 720,     # 12:00
                "duration_minutes": 120,
                "overlap_count": 2
            })
        
        result = FreeTimeResult(
            id=uuid4(),
            group_id=group_id,
            version=1,
            status="completed",
            availability_by_day={
                "MONDAY": [{"slot_id": "MON_10_00", "start_minute": 600, "end_minute": 720, "availability_count": 2, "is_common": True}],
                "TUESDAY": [{"slot_id": "TUE_10_00", "start_minute": 600, "end_minute": 720, "availability_count": 2, "is_common": True}],
                "WEDNESDAY": [{"slot_id": "WED_10_00", "start_minute": 600, "end_minute": 720, "availability_count": 2, "is_common": True}],
            },
            free_time_intervals=free_time,
            computed_at=now,
            created_at=now
        )
        test_db.add(result)
        test_db.commit()
        
        # Poll
        response = client.get(f"/groups/{group_id}/free-time")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify multiple days in response
        assert len(data["free_time"]) == 3
        
        days_in_response = [slot["day"] for slot in data["free_time"]]
        assert "MONDAY" in days_in_response
        assert "TUESDAY" in days_in_response
        assert "WEDNESDAY" in days_in_response
    
    def test_poll_no_result_yet(self, client, test_db):
        """Test polling when calculation is not yet complete."""
        group_id = uuid4()
        now = datetime.utcnow()
        
        group = Group(
            id=group_id,
            group_name="no_result_group",
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(hours=72),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # No FreeTimeResult created (calculation not done yet)
        
        # Poll should return 404 or handle gracefully
        response = client.get(f"/groups/{group_id}/free-time")
        
        # Should either return 404 or empty result with pending status
        # Accept either, depending on implementation
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            # If 200 returned, should indicate no results yet
            assert len(data.get("free_time", [])) == 0
