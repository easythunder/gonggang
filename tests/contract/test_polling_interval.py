"""
Contract tests for polling interval enforcement (T054)

Tests:
- test_interval_header: X-Poll-Wait header always between 2000-3000ms
- test_rapid_requests_throttled: Rapid requests get enforced min wait
"""
import pytest
import time
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.models.group import Group
from src.models.free_time_result import FreeTimeResult
from src.database import Base


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


class TestPollingIntervalEnforcement:
    """Test server-enforced polling intervals."""
    
    def test_interval_header_always_present(self, client, test_db):
        """Test X-Poll-Wait header is always 2000-3000ms."""
        group_id = uuid4()
        now = datetime.utcnow()
        
        # Setup group and result
        group = Group(
            id=group_id,
            group_name="polling_group",
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
        
        # Perform multiple requests
        for i in range(5):
            response = client.get(f"/groups/{group_id}/free-time")
            
            assert response.status_code == 200
            assert "X-Poll-Wait" in response.headers
            
            poll_wait = int(response.headers["X-Poll-Wait"])
            assert 2000 <= poll_wait <= 3000, f"X-Poll-Wait {poll_wait} not in range"
    
    def test_client_interval_ignored(self, client, test_db):
        """Test that client's interval_ms query param is ignored."""
        group_id = uuid4()
        now = datetime.utcnow()
        
        # Setup
        group = Group(
            id=group_id,
            group_name="ignored_interval_group",
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
        
        # Test: Client requests very fast interval (100ms)
        response = client.get(
            f"/groups/{group_id}/free-time",
            params={"interval_ms": 100}
        )
        
        assert response.status_code == 200
        poll_wait = int(response.headers["X-Poll-Wait"])
        # Server should still enforce 2000-3000
        assert poll_wait >= 2000, "Server did not enforce minimum interval"
        
        # Test: Client requests very long interval (60000ms = 1min)
        response = client.get(
            f"/groups/{group_id}/free-time",
            params={"interval_ms": 60000}
        )
        
        assert response.status_code == 200
        poll_wait = int(response.headers["X-Poll-Wait"])
        # Server should still enforce 2000-3000, not 60000
        assert poll_wait <= 3000, "Server did not override client interval"
    
    def test_response_time_header(self, client, test_db):
        """Test X-Response-Time header tracks request duration."""
        group_id = uuid4()
        now = datetime.utcnow()
        
        # Setup
        group = Group(
            id=group_id,
            group_name="response_time_group",
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
        
        # Execute
        response = client.get(f"/groups/{group_id}/free-time")
        
        assert response.status_code == 200
        assert "X-Response-Time" in response.headers
        
        response_time = int(response.headers["X-Response-Time"])
        assert response_time >= 0
        assert response_time < 5000  # Should be fast (< 5 seconds)
    
    def test_calculation_version_header(self, client, test_db):
        """Test X-Calculation-Version header matches result version."""
        group_id = uuid4()
        now = datetime.utcnow()
        
        # Setup
        group = Group(
            id=group_id,
            group_name="version_group",
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(hours=72),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        
        # Create result with specific version
        result = FreeTimeResult(
            id=uuid4(),
            group_id=group_id,
            version=5,  # Specific version
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
        
        assert response.status_code == 200
        assert "X-Calculation-Version" in response.headers
        assert response.headers["X-Calculation-Version"] == "5"
    
    def test_all_response_headers_together(self, client, test_db):
        """Test all three response headers are present together."""
        group_id = uuid4()
        now = datetime.utcnow()
        
        group = Group(
            id=group_id,
            group_name="all_headers_group",
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
            version=2,
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
        
        assert response.status_code == 200
        
        # All three headers must be present
        headers = response.headers
        assert "X-Poll-Wait" in headers
        assert "X-Response-Time" in headers
        assert "X-Calculation-Version" in headers
        
        # Verify values are parseable as integers
        poll_wait = int(headers["X-Poll-Wait"])
        response_time = int(headers["X-Response-Time"])
        version = int(headers["X-Calculation-Version"])
        
        assert isinstance(poll_wait, int)
        assert isinstance(response_time, int)
        assert isinstance(version, int)
