"""Contract tests for URL submission API endpoint.

These tests validate the POST /api/submissions/url endpoint.
"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def _create_group() -> dict:
    """Helper: create a group and return response data."""
    response = client.post(
        "/groups",
        json={"display_unit_minutes": 30}
    )
    assert response.status_code == 201
    return response.json()["data"]


class TestSubmitUrlContract:
    """Test POST /api/submissions/url endpoint contract."""

    def test_submit_url_success(self):
        """Test successful URL submission."""
        group = _create_group()

        response = client.post(
            "/api/submissions/url",
            json={
                "group_id": group["group_id"],
                "nickname": "url_test_user",
                "url": "https://everytime.kr/@abc123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["submission_id"]
        assert data["nickname"] == "url_test_user"
        assert data["group_id"] == group["group_id"]
        assert data["type"] == "link"
        assert data["url"] == "https://everytime.kr/@abc123"
        assert "status" in data
        assert "created_at" in data

    def test_submit_url_response_has_timing_header(self):
        """Test that URL submission response includes X-Response-Time header."""
        group = _create_group()

        response = client.post(
            "/api/submissions/url",
            json={
                "group_id": group["group_id"],
                "nickname": "timing_user",
                "url": "https://example.com/schedule",
            },
        )

        assert response.status_code == 201
        assert "X-Response-Time" in response.headers

    def test_submit_url_invalid_url_format(self):
        """Test rejection of invalid URL format."""
        group = _create_group()

        response = client.post(
            "/api/submissions/url",
            json={
                "group_id": group["group_id"],
                "nickname": "test_user",
                "url": "not-a-valid-url",
            },
        )

        assert response.status_code == 422

    def test_submit_url_missing_url(self):
        """Test rejection when URL is missing."""
        group = _create_group()

        response = client.post(
            "/api/submissions/url",
            json={
                "group_id": group["group_id"],
                "nickname": "test_user",
            },
        )

        assert response.status_code == 422

    def test_submit_url_invalid_group_id(self):
        """Test rejection of invalid group_id format."""
        response = client.post(
            "/api/submissions/url",
            json={
                "group_id": "not-a-uuid",
                "nickname": "test_user",
                "url": "https://example.com/schedule",
            },
        )

        assert response.status_code == 422

    def test_submit_url_group_not_found(self):
        """Test that non-existent group returns 404."""
        import uuid

        response = client.post(
            "/api/submissions/url",
            json={
                "group_id": str(uuid.uuid4()),
                "nickname": "test_user",
                "url": "https://example.com/schedule",
            },
        )

        assert response.status_code == 404

    def test_submit_url_duplicate_nickname(self):
        """Test rejection of duplicate nickname in same group."""
        group = _create_group()

        # First submission succeeds
        response1 = client.post(
            "/api/submissions/url",
            json={
                "group_id": group["group_id"],
                "nickname": "dup_url_user",
                "url": "https://example.com/schedule1",
            },
        )
        assert response1.status_code == 201

        # Second submission with same nickname fails
        response2 = client.post(
            "/api/submissions/url",
            json={
                "group_id": group["group_id"],
                "nickname": "dup_url_user",
                "url": "https://example.com/schedule2",
            },
        )
        assert response2.status_code == 409

    def test_submit_url_empty_nickname(self):
        """Test rejection of empty nickname."""
        group = _create_group()

        response = client.post(
            "/api/submissions/url",
            json={
                "group_id": group["group_id"],
                "nickname": "",
                "url": "https://example.com/schedule",
            },
        )

        assert response.status_code == 422

    def test_submit_url_nickname_too_long(self):
        """Test rejection of nickname exceeding 50 characters."""
        group = _create_group()

        response = client.post(
            "/api/submissions/url",
            json={
                "group_id": group["group_id"],
                "nickname": "a" * 51,
                "url": "https://example.com/schedule",
            },
        )

        assert response.status_code == 422

    def test_submit_url_then_get_submission(self):
        """Test that URL submission can be retrieved via GET endpoint."""
        group = _create_group()

        # Submit URL
        submit_response = client.post(
            "/api/submissions/url",
            json={
                "group_id": group["group_id"],
                "nickname": "get_test_user",
                "url": "https://everytime.kr/@xyz789",
            },
        )
        assert submit_response.status_code == 201
        submission_id = submit_response.json()["submission_id"]

        # Retrieve submission
        get_response = client.get(f"/api/submissions/{submission_id}")
        assert get_response.status_code == 200

        data = get_response.json()
        assert data["submission_id"] == submission_id
        assert data["nickname"] == "get_test_user"
        assert data["type"] == "link"
        assert data["payload_ref"] == "https://everytime.kr/@xyz789"

    def test_submit_url_appears_in_group_submissions(self):
        """Test that URL submission appears in group submission list."""
        group = _create_group()

        # Submit URL
        client.post(
            "/api/submissions/url",
            json={
                "group_id": group["group_id"],
                "nickname": "list_test_user",
                "url": "https://example.com/schedule",
            },
        )

        # List group submissions
        list_response = client.get(
            f"/api/groups/{group['group_id']}/submissions"
        )
        assert list_response.status_code == 200

        data = list_response.json()
        assert data["total_count"] >= 1

        nicknames = [s["nickname"] for s in data["submissions"]]
        assert "list_test_user" in nicknames

        # Verify type is included
        url_sub = next(
            s for s in data["submissions"] if s["nickname"] == "list_test_user"
        )
        assert url_sub["type"] == "link"

    def test_submit_url_http_protocol(self):
        """Test that HTTP URLs are accepted."""
        group = _create_group()

        response = client.post(
            "/api/submissions/url",
            json={
                "group_id": group["group_id"],
                "nickname": "http_user",
                "url": "http://example.com/schedule",
            },
        )

        assert response.status_code == 201

    def test_submit_url_with_path_and_query(self):
        """Test that URLs with paths and query parameters are accepted."""
        group = _create_group()

        response = client.post(
            "/api/submissions/url",
            json={
                "group_id": group["group_id"],
                "nickname": "complex_url_user",
                "url": "https://everytime.kr/timetable/view/123?semester=2026-1",
            },
        )

        assert response.status_code == 201
        assert response.json()["url"] == "https://everytime.kr/timetable/view/123?semester=2026-1"
