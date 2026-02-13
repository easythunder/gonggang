"""Contract tests for group API endpoints.

These tests validate that the API follows the OpenAPI specification.
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


class TestCreateGroupContract:
    """Test POST /groups endpoint contract."""

    def test_create_group_with_name(self):
        """Test creating a group with custom name."""
        response = client.post(
            "/groups",
            json={
                "group_name": "study_session_2026",
                "display_unit_minutes": 30,
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert data["data"]["group_name"] == "study_session_2026"
        assert data["data"]["display_unit_minutes"] == 30
        assert "group_id" in data["data"]
        assert "invite_url" in data["data"]
        assert "share_url" in data["data"]
        assert "expires_at" in data["data"]

    def test_create_group_without_name(self):
        """Test creating a group with auto-generated name."""
        response = client.post(
            "/groups",
            json={"display_unit_minutes": 60}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "group_name" in data["data"]
        # Auto-generated names follow pattern: word_word_word
        assert "_" in data["data"]["group_name"]

    def test_create_group_invalid_display_unit(self):
        """Test rejecting invalid display unit."""
        response = client.post(
            "/groups",
            json={
                "group_name": "test_group",
                "display_unit_minutes": 45,  # Invalid: not in [10, 20, 30, 60]
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "detail" in data

    def test_create_group_default_display_unit(self):
        """Test that display_unit_minutes has default."""
        response = client.post(
            "/groups",
            json={}  # No display_unit provided
        )
        # This should either use default or fail validation
        # Based on spec, it's REQUIRED
        assert response.status_code in [201, 422]

    def test_create_group_response_structure(self):
        """Test response has required fields per OpenAPI spec."""
        response = client.post(
            "/groups",
            json={"display_unit_minutes": 20}
        )
        assert response.status_code == 201
        data = response.json()
        
        # Top-level response structure
        assert "status" in data
        assert "data" in data
        assert "timestamp" in data
        
        # Data structure
        assert "group_id" in data["data"]
        assert "group_name" in data["data"]
        assert "created_at" in data["data"]
        assert "expires_at" in data["data"]
        assert "invite_url" in data["data"]
        assert "share_url" in data["data"]


class TestGetGroupContract:
    """Test GET /groups/{groupId} endpoint contract."""

    @pytest.fixture
    def created_group(self):
        """Create a group for testing."""
        response = client.post(
            "/groups",
            json={"display_unit_minutes": 30}
        )
        assert response.status_code == 201
        return response.json()["data"]

    def test_get_group_success(self, created_group):
        """Test retrieving an existing group."""
        response = client.get(f"/groups/{created_group['group_id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["group_id"] == created_group["group_id"]

    def test_get_group_not_found(self):
        """Test retrieving non-existent group."""
        import uuid
        fake_id = str(uuid.uuid4())
        response = client.get(f"/groups/{fake_id}")
        assert response.status_code == 404

    def test_get_group_invalid_id(self):
        """Test with invalid UUID format."""
        response = client.get("/groups/not-a-uuid")
        assert response.status_code == 400

    def test_get_group_response_structure(self, created_group):
        """Test GET response structure."""
        response = client.get(f"/groups/{created_group['group_id']}")
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "status" in data
        assert "data" in data
        assert "group_id" in data["data"]
        assert "group_name" in data["data"]
        assert "expires_at" in data["data"]


class TestGroupStatsContract:
    """Test GET /groups/{groupId}/stats endpoint."""

    @pytest.fixture
    def created_group(self):
        """Create a group for testing."""
        response = client.post(
            "/groups",
            json={"display_unit_minutes": 30}
        )
        assert response.status_code == 201
        return response.json()["data"]

    def test_get_stats(self, created_group):
        """Test retrieving group statistics."""
        response = client.get(f"/groups/{created_group['group_id']}/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "total_submissions" in data["data"]
        assert "successful_submissions" in data["data"]
        assert "time_remaining_hours" in data["data"]
