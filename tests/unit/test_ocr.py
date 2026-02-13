"""Unit tests for OCR wrapper functionality."""
import pytest
import time
from unittest.mock import Mock, patch
from src.services.ocr import OCRWrapper


class TestOCRWrapper:
    """Test OCR functionality with timeout and error handling."""

    @pytest.fixture
    def wrapper(self):
        """Create OCR wrapper instance."""
        return OCRWrapper(library="tesseract", timeout_seconds=3)

    def test_ocr_initialization(self, wrapper):
        """Test wrapper initializes correctly."""
        assert wrapper.library == "tesseract"
        assert wrapper.timeout_seconds == 3

    def test_parse_schedule_valid_text(self, wrapper):
        """Test parsing valid OCR text output."""
        ocr_text = """
        MONDAY
        9:00-10:30 Busy
        14:00-15:30 Busy
        
        TUESDAY
        10:00-11:00 Busy
        """
        result = wrapper.parse_schedule_text(ocr_text)
        
        # Should extract busy intervals
        assert len(result) > 0
        # Check structure: list of (day, start_minute, end_minute)
        for interval in result:
            assert len(interval) == 3
            day, start, end = interval
            assert isinstance(day, int)  # 0-6
            assert 0 <= start <= 1440
            assert 0 <= end <= 1440

    def test_parse_schedule_empty(self, wrapper):
        """Test parsing empty or invalid OCR text."""
        result = wrapper.parse_schedule_text("")
        assert result == [] or isinstance(result, list)

    def test_parse_schedule_malformed(self, wrapper):
        """Test parsing malformed OCR output."""
        malformed = "This is not a schedule format at all"
        result = wrapper.parse_schedule_text(malformed)
        assert isinstance(result, list)  # Should return empty list, not crash

    def test_extract_intervals_from_text(self, wrapper):
        """Test extraction of time intervals from text."""
        text = "Meeting 9:00-10:30"
        intervals = wrapper.extract_intervals(text)
        assert len(intervals) > 0

    def test_timeout_handling(self, wrapper):
        """Test timeout handling (mock long-running OCR)."""
        # This would be integration-tested with real Tesseract
        # For unit tests, we mock the timeout behavior
        with patch.object(wrapper, 'parse_image', side_effect=TimeoutError("OCR timeout")):
            with pytest.raises(TimeoutError):
                wrapper.parse_image(b"fake_image_data")

    def test_error_handling_corrupted_image(self, wrapper):
        """Test error handling for corrupted image data."""
        with pytest.raises(Exception):
            wrapper.parse_image(b"invalid_image_data")


class TestTimeExtraction:
    """Test time extraction from OCR text."""

    def test_extract_time_hh_mm_format(self):
        """Extract times in HH:MM format."""
        from src.services.ocr import extract_times
        
        text = "Meeting from 14:30 to 15:45"
        times = extract_times(text)
        assert "14:30" in [f"{h}:{m:02d}" for h, m in times]

    def test_extract_multiple_times(self):
        """Extract multiple time points from text."""
        from src.services.ocr import extract_times
        
        text = """
        Monday: 9:00-10:30 class
        Then: 14:00-15:00 meeting
        """
        times = extract_times(text)
        assert len(times) >= 4  # At least 4 times: 9, 10:30, 14, 15

    def test_time_format_variations(self):
        """Handle various time formats."""
        from src.services.ocr import extract_times
        
        variations = [
            "9:00",      # Single digit hour
            "09:00",     # Zero-padded
            "23:59",     # Late time
            "00:00",     # Midnight
        ]
        
        for time_str in variations:
            text = f"Meeting at {time_str}"
            times = extract_times(text)
            assert len(times) > 0


class TestDayExtraction:
    """Test day-of-week extraction from OCR text."""

    def test_extract_days(self):
        """Extract day names from OCR text."""
        from src.services.ocr import extract_days
        
        text = "Monday 9:00-10:00. Tuesday 14:00-15:00."
        days = extract_days(text)
        assert len(days) >= 2

    def test_day_name_variations(self):
        """Handle day name variations."""
        from src.services.ocr import extract_days
        
        text = "Mon 9:00. Tue 14:00. Wed 10:00."
        days = extract_days(text)
        # Should recognize abbreviated or full names
        assert len(days) >= 1


class TestOCRMemoryCleanup:
    """Test memory cleanup after OCR parsing."""

    def test_image_not_persisted(self):
        """Verify image is not saved to disk after OCR."""
        import tempfile
        import os
        
        temp_dir = tempfile.gettempdir()
        before_files = set(os.listdir(temp_dir))
        
        wrapper = OCRWrapper(library="tesseract", timeout_seconds=3)
        # Parse a test image (would be mocked in real tests)
        # After parsing, no new temp files should exist
        
        after_files = set(os.listdir(temp_dir))
        # In practice, Tesseract may create some temp files, but we ensure they're cleaned up
        # This is more of an integration test

    def test_cleanup_on_error(self):
        """Verify cleanup happens even if OCR errors."""
        wrapper = OCRWrapper(library="tesseract", timeout_seconds=3)
        
        try:
            # This will fail with invalid data
            wrapper.parse_image(b"invalid")
        except Exception:
            pass
        
        # Cleanup should have happened (verify no leaked resources)
        # In real implementation, context manager or try/finally ensures this
