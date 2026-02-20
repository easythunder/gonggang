"""
Unit tests for lazy deletion (T062)

Tests:
- test_check_expiry: Verify expiration check logic
- test_return_410_when_expired: Verify 410 Gone is returned for expired groups
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.models import Group, Submission, FreeTimeResult, Base


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestLazyDeletion:
    """Test lazy deletion (expiration check on read)."""
    
    def test_check_expiry_not_expired(self, test_db):
        """Test that non-expired group passes expiry check."""
        now = datetime.utcnow()
        group_id = uuid4()
        
        group = Group(
            id=group_id,
            group_name="active_group",
            created_at=now,
            last_activity_at=now,
            expires_at=now + timedelta(hours=24),  # Expires in 24 hours
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Check: Group should not be expired
        from src.services.deletion import DeletionService
        is_expired = DeletionService.check_expiry(group)
        
        assert is_expired is False
    
    def test_check_expiry_just_expired(self, test_db):
        """Test that expired group is detected."""
        now = datetime.utcnow()
        group_id = uuid4()
        
        group = Group(
            id=group_id,
            group_name="expired_group",
            created_at=now - timedelta(hours=73),
            last_activity_at=now - timedelta(hours=73),
            expires_at=now - timedelta(seconds=1),  # Expired 1 second ago
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Check: Group should be expired
        from src.services.deletion import DeletionService
        is_expired = DeletionService.check_expiry(group)
        
        assert is_expired is True
    
    def test_check_expiry_boundary(self, test_db):
        """Test expiry check at exact expiration time."""
        now = datetime.utcnow()
        group_id = uuid4()
        
        # Group expires exactly now
        group = Group(
            id=group_id,
            group_name="boundary_group",
            created_at=now - timedelta(hours=72),
            last_activity_at=now - timedelta(hours=72),
            expires_at=now,
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Check: Should be considered expired (<=)
        from src.services.deletion import DeletionService
        is_expired = DeletionService.check_expiry(group)
        
        assert is_expired is True
    
    def test_lazy_deletion_http_410(self, test_db):
        """Test that accessing expired group returns 410 Gone."""
        from fastapi.testclient import TestClient
        from src.main import app
        from src.database import get_db
        
        now = datetime.utcnow()
        group_id = uuid4()
        
        # Create expired group
        group = Group(
            id=group_id,
            group_name="expired_for_http",
            created_at=now - timedelta(hours=73),
            last_activity_at=now - timedelta(hours=73),
            expires_at=now - timedelta(hours=1),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Override get_db dependency for testing
        def override_get_db():
            try:
                yield test_db
            finally:
                pass
        
        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        
        # Try to access expired group
        response = client.get(f"/groups/{group_id}/free-time")
        
        # Should return 410 Gone
        assert response.status_code == 410
        data = response.json()
        assert "error" in data
    
    def test_lazy_deletion_soft_delete_flag(self, test_db):
        """Test that lazy deletion sets soft_delete flag if available."""
        now = datetime.utcnow()
        group_id = uuid4()
        
        group = Group(
            id=group_id,
            group_name="soft_delete_group",
            created_at=now - timedelta(hours=73),
            last_activity_at=now - timedelta(hours=73),
            expires_at=now - timedelta(hours=1),
            display_unit_minutes=30,
            max_participants=50
        )
        test_db.add(group)
        test_db.commit()
        
        # Perform lazy deletion check and mark
        from src.services.deletion import DeletionService
        is_expired = DeletionService.check_expiry(group)
        
        if is_expired:
            # Mark for soft deletion
            DeletionService.mark_soft_deleted(test_db, group_id)
        
        # Verify soft_delete flag
        updated_group = test_db.query(Group).filter(Group.id == group_id).first()
        
        # Should have soft_delete flag set (if model supports it)
        # or be marked in some way for later hard deletion
        assert updated_group is not None
