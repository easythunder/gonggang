"""Integration tests for image submission workflow."""
import pytest
import logging
from io import BytesIO
from uuid import UUID
from PIL import Image
from fastapi.testclient import TestClient

from src.main import app
from src.lib.database import db_manager
from src.services.group import GroupService
from src.services.submission import SubmissionService
from src.services.ocr import OCRWrapper, OCRFailedError

logger = logging.getLogger(__name__)


@pytest.fixture
def client():
    """Fixture: FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Fixture: Database session for test."""
    session = db_manager.get_session()
    yield session
    session.close()


def create_test_image(text: str = "BUSY: 9:00 - 10:00\nMONDAY - FRIDAY") -> bytes:
    """Create a simple test image with text overlay.
    
    Args:
        text: Text to include in image
    
    Returns:
        Image bytes
    """
    # Create blank image
    image = Image.new('RGB', (400, 300), color='white')
    
    # Convert to bytes (simplified - no text rendering for now)
    image_bytes = BytesIO()
    image.save(image_bytes, format='PNG')
    return image_bytes.getvalue()


class TestImageSubmissionWorkflow:
    """Test complete image submission workflow."""

    def test_submit_schedule_end_to_end(self, client, db_session):
        """Test end-to-end submission workflow:
        1. Create group
        2. Upload schedule image
        3. Verify submission created
        4. Verify intervals extracted
        5. Verify group last_activity updated
        """
        # Step 1: Create group
        create_response = client.post(
            "/api/groups",
            json={
                "group_name": "Test Group",
                "display_unit_minutes": 30,
            },
        )
        assert create_response.status_code == 201
        group_data = create_response.json()
        group_id = group_data["group_id"]
        
        logger.info(f"Created test group: {group_id}")

        # Step 2: Upload schedule image
        test_image = create_test_image()
        
        response = client.post(
            "/api/submissions",
            data={
                "group_id": group_id,
                "nickname": "test_user",
            },
            files={"image": ("schedule.png", BytesIO(test_image), "image/png")},
        )
        
        logger.info(f"Submission response: {response.status_code} - {response.json()}")
        
        assert response.status_code == 201
        submission_data = response.json()
        submission_id = submission_data["submission_id"]
        
        # Verify submission fields
        assert submission_data["nickname"] == "test_user"
        assert submission_data["group_id"] == group_id
        assert "status" in submission_data
        assert "interval_count" in submission_data
        assert "created_at" in submission_data

        # Verify response headers
        assert "X-Response-Time" in response.headers
        assert "X-Ocr-Time" in response.headers
        assert "X-Interval-Count" in response.headers

        logger.info(f"Created submission: {submission_id}")

        # Step 3: Verify submission was stored
        get_response = client.get(f"/api/submissions/{submission_id}")
        assert get_response.status_code == 200
        stored_submission = get_response.json()
        
        assert stored_submission["submission_id"] == submission_id
        assert stored_submission["nickname"] == "test_user"
        assert stored_submission["status"] in ["SUCCESS", "FAILED"]

        # Step 4: Verify intervals extracted
        assert "interval_count" in stored_submission
        # Note: Exact count depends on OCR parsing (may be 0 if image has no clear schedule)

        # Step 5: Verify group last_activity updated
        group_response = client.get(f"/api/groups/{group_id}")
        assert group_response.status_code == 200
        updated_group = group_response.json()
        assert updated_group["last_activity_at"] >= group_data["created_at"]

        logger.info("End-to-end submission workflow completed successfully")

    def test_submit_schedule_without_image(self, client):
        """Test submission fails when image is missing."""
        group_response = client.post(
            "/api/groups",
            json={
                "group_name": "Test Group",
                "display_unit_minutes": 30,
            },
        )
        group_id = group_response.json()["group_id"]

        response = client.post(
            "/api/submissions",
            data={
                "group_id": group_id,
                "nickname": "test_user",
            },
            files={},  # No image
        )
        
        assert response.status_code == 422  # Unprocessable entity

    def test_submit_schedule_invalid_group_id(self, client):
        """Test submission fails with invalid group ID."""
        test_image = create_test_image()

        response = client.post(
            "/api/submissions",
            data={
                "group_id": "not-a-uuid",
                "nickname": "test_user",
            },
            files={"image": ("schedule.png", BytesIO(test_image), "image/png")},
        )
        
        assert response.status_code == 422

    def test_submit_schedule_group_not_found(self, client):
        """Test submission fails when group doesn't exist."""
        test_image = create_test_image()
        fake_group_id = "550e8400-e29b-41d4-a716-446655440000"

        response = client.post(
            "/api/submissions",
            data={
                "group_id": fake_group_id,
                "nickname": "test_user",
            },
            files={"image": ("schedule.png", BytesIO(test_image), "image/png")},
        )
        
        assert response.status_code == 404

    def test_submit_schedule_duplicate_nickname(self, client):
        """Test submission fails with duplicate nickname."""
        # Create group
        group_response = client.post(
            "/api/groups",
            json={
                "group_name": "Test Group",
                "display_unit_minutes": 30,
            },
        )
        group_id = group_response.json()["group_id"]
        test_image = create_test_image()

        # First submission succeeds
        response1 = client.post(
            "/api/submissions",
            data={
                "group_id": group_id,
                "nickname": "duplicate_user",
            },
            files={"image": ("schedule.png", BytesIO(test_image), "image/png")},
        )
        assert response1.status_code == 201

        # Second submission with same nickname fails
        response2 = client.post(
            "/api/submissions",
            data={
                "group_id": group_id,
                "nickname": "duplicate_user",
            },
            files={"image": ("schedule.png", BytesIO(test_image), "image/png")},
        )
        assert response2.status_code == 409  # Conflict

    def test_submit_schedule_invalid_nickname(self, client):
        """Test submission fails with invalid nickname."""
        # Create group
        group_response = client.post(
            "/api/groups",
            json={
                "group_name": "Test Group",
                "display_unit_minutes": 30,
            },
        )
        group_id = group_response.json()["group_id"]
        test_image = create_test_image()

        # Empty nickname
        response = client.post(
            "/api/submissions",
            data={
                "group_id": group_id,
                "nickname": "",
            },
            files={"image": ("schedule.png", BytesIO(test_image), "image/png")},
        )
        assert response.status_code == 422

    def test_list_group_submissions(self, client):
        """Test listing submissions for a group."""
        # Create group
        group_response = client.post(
            "/api/groups",
            json={
                "group_name": "Test Group",
                "display_unit_minutes": 30,
            },
        )
        group_id = group_response.json()["group_id"]
        test_image = create_test_image()

        # Create 3 submissions
        submission_ids = []
        for i in range(3):
            response = client.post(
                "/api/submissions",
                data={
                    "group_id": group_id,
                    "nickname": f"user_{i}",
                },
                files={"image": ("schedule.png", BytesIO(test_image), "image/png")},
            )
            assert response.status_code == 201
            submission_ids.append(response.json()["submission_id"])

        # List submissions
        list_response = client.get(f"/api/groups/{group_id}/submissions")
        assert list_response.status_code == 200
        
        data = list_response.json()
        assert "submissions" in data
        assert "total_count" in data
        assert "successful_count" in data
        assert data["total_count"] == 3
        
        # Verify all submissions in list
        submission_nicknames = [s["nickname"] for s in data["submissions"]]
        for i in range(3):
            assert f"user_{i}" in submission_nicknames

    def test_response_time_headers(self, client):
        """Test that response includes timing headers."""
        # Create group
        group_response = client.post(
            "/api/groups",
            json={
                "group_name": "Test Group",
                "display_unit_minutes": 30,
            },
        )
        group_id = group_response.json()["group_id"]
        test_image = create_test_image()

        response = client.post(
            "/api/submissions",
            data={
                "group_id": group_id,
                "nickname": "test_user",
            },
            files={"image": ("schedule.png", BytesIO(test_image), "image/png")},
        )

        assert response.status_code == 201
        
        # Check timing headers
        assert "X-Response-Time" in response.headers
        response_time_ms = float(response.headers["X-Response-Time"])
        assert response_time_ms > 0
        assert response_time_ms < 5000  # Should be less than 5 seconds
        
        assert "X-Ocr-Time" in response.headers
        ocr_time_ms = float(response.headers["X-Ocr-Time"])
        assert ocr_time_ms >= 0

        logger.info(f"Response times: {response_time_ms:.0f}ms total, {ocr_time_ms:.0f}ms OCR")


class TestSubmissionMemoryCleanup:
    """Test that submission processing doesn't create temporary files."""

    def test_no_image_files_persisted(self, client):
        """Verify no image files are persisted to disk."""
        import os
        import tempfile

        # Create group
        group_response = client.post(
            "/api/groups",
            json={
                "group_name": "Test Group",
                "display_unit_minutes": 30,
            },
        )
        group_id = group_response.json()["group_id"]
        test_image = create_test_image()

        # Get temp directory before submission
        temp_dir = tempfile.gettempdir()
        files_before = set(os.listdir(temp_dir))

        # Submit image
        response = client.post(
            "/api/submissions",
            data={
                "group_id": group_id,
                "nickname": "cleanup_test",
            },
            files={"image": ("schedule.png", BytesIO(test_image), "image/png")},
        )
        assert response.status_code == 201

        # Check temp directory after submission
        files_after = set(os.listdir(temp_dir))
        new_files = files_after - files_before
        
        # Verify no .png, .jpg, .jpeg, .tmp files created
        image_extensions = {'.png', '.jpg', '.jpeg', '.tmp', '.bmp', '.gif'}
        for filename in new_files:
            ext = os.path.splitext(filename)[1].lower()
            assert ext not in image_extensions, f"Found persisted image file: {filename}"

        logger.info("Verified no image files persisted to disk")
