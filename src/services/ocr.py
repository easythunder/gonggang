"""OCR wrapper service for schedule image parsing.

Supports Tesseract and PaddleOCR with timeout handling.
Images are processed in memory only - never saved to disk.
"""
import logging
import re
from io import BytesIO
from typing import List, Tuple, Optional
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


class OCRTimeoutError(Exception):
    """Raised when OCR parsing times out."""
    pass


class OCRFailedError(Exception):
    """Raised when OCR parsing fails."""
    pass


class OCRWrapper:
    """Wrapper for OCR functionality with timeout and error handling."""

    def __init__(self, library: str = "tesseract", timeout_seconds: int = 3):
        """Initialize OCR wrapper.
        
        Args:
            library: 'tesseract' or 'paddleocr'
            timeout_seconds: Timeout for OCR operation
        """
        self.library = library
        self.timeout_seconds = timeout_seconds
        logger.info(f"Initialized OCR wrapper: {library} ({timeout_seconds}s timeout)")

    def parse_image(self, image_bytes: bytes) -> str:
        """Parse an image and extract text using OCR (memory-only).
        
        Args:
            image_bytes: Image file content as bytes
        
        Returns:
            Extracted text from image
        
        Raises:
            OCRTimeoutError: If OCR exceeds timeout
            OCRFailedError: If OCR cannot parse the image
        """
        if not image_bytes:
            raise OCRFailedError("Empty image data")

        try:
            # Load image from bytes into memory (no disk storage)
            image_stream = BytesIO(image_bytes)
            image = Image.open(image_stream)
            
            # Validate image
            if image.size == (0, 0):
                logger.warning("Image has zero size")
                raise OCRFailedError("Invalid image dimensions")

            logger.debug(f"Parsing image: {image.size} {image.format}")
            
            # Parse with timeout
            if self.library == "tesseract":
                text = self._parse_with_tesseract(image)
            elif self.library == "paddleocr":
                text = self._parse_with_paddleocr(image)
            else:
                raise ValueError(f"Unsupported OCR library: {self.library}")

            logger.info(f"OCR parsing successful: {len(text)} chars extracted")
            return text

        except Image.UnidentifiedImageError:
            logger.error("Invalid image format")
            raise OCRFailedError("Invalid image format - cannot identify")
        except OCRTimeoutError:
            logger.error(f"OCR timeout exceeded ({self.timeout_seconds}s)")
            raise
        except OCRFailedError:
            raise
        except Exception as e:
            logger.error(f"OCR parsing failed: {e}", exc_info=True)
            raise OCRFailedError(f"OCR parsing failed: {str(e)}")
        finally:
            # Ensure image and stream are garbage-collected
            # (Important for memory-only processing)
            image_stream.close()

    def _parse_with_tesseract(self, image: Image.Image) -> str:
        """Parse image with Tesseract OCR."""
        import signal

        def timeout_handler(signum, frame):
            raise OCRTimeoutError(f"Tesseract OCR timeout after {self.timeout_seconds}s")

        # Set alarm (Unix only)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.timeout_seconds)

        try:
            text = pytesseract.image_to_string(image, lang="eng")
            signal.alarm(0)  # Cancel alarm
            return text
        except OCRTimeoutError:
            raise
        except Exception as e:
            signal.alarm(0)  # Cancel alarm
            raise OCRFailedError(f"Tesseract error: {e}")

    def _parse_with_paddleocr(self, image: Image.Image) -> str:
        """Parse image with PaddleOCR."""
        try:
            # This would require PaddleOCR installation
            # For now, raise not implemented
            raise NotImplementedError("PaddleOCR not yet integrated")
        except NotImplementedError:
            raise
        except Exception as e:
            raise OCRFailedError(f"PaddleOCR error: {e}")

    def parse_schedule_text(self, ocr_text: str) -> List[Tuple[int, int, int, int]]:
        """Parse OCR text to extract schedule intervals.
        
        Args:
            ocr_text: Raw text from OCR
        
        Returns:
            List of (day_of_week, start_minute, end_minute) tuples
            day_of_week: 0-6 (Monday-Sunday)
            start_minute: 0-1439
            end_minute: 0-1439
        """
        if not ocr_text or not ocr_text.strip():
            logger.warning("Empty OCR text")
            return []

        intervals = []
        
        # Extract day and time combinations
        days = self._extract_days(ocr_text)
        times = self._extract_times(ocr_text)
        
        logger.debug(f"Found {len(days)} days, {len(times)} time points")

        # Simple heuristic: match days with following time intervals
        # This is a simplified parser - real implementation would be more robust
        for day_num in days:
            # Find times that follow this day in the text
            for start_time, end_time in times:
                if start_time < end_time:
                    intervals.append((day_num, start_time, end_time))

        logger.info(f"Extracted {len(intervals)} schedule intervals from OCR text")
        return intervals

    def extract_intervals(self, text: str) -> List[Tuple[int, int, int]]:
        """Extract time intervals (start, end, day) from text."""
        return self.parse_schedule_text(text)

    def _extract_days(self, text: str) -> List[int]:
        """Extract day numbers (0-6) from text."""
        days_map = {
            "monday": 0, "mon": 0,
            "tuesday": 1, "tue": 1, "tues": 1,
            "wednesday": 2, "wed": 2,
            "thursday": 3, "thu": 3, "thurs": 3,
            "friday": 4, "fri": 4,
            "saturday": 5, "sat": 5,
            "sunday": 6, "sun": 6,
        }
        
        found_days = set()
        text_lower = text.lower()
        
        for day_name, day_num in days_map.items():
            if day_name in text_lower:
                found_days.add(day_num)
        
        return sorted(list(found_days))

    def _extract_times(self, text: str) -> List[Tuple[int, int]]:
        """Extract time intervals (start_minute, end_minute) from text."""
        # Pattern: HH:MM or H:MM (optionally with AM/PM)
        # Matches: 9:30, 09:00, 14:30, etc.
        time_pattern = r'(\d{1,2}):(\d{2})'
        matches = re.findall(time_pattern, text)
        
        times = []
        for hour_str, min_str in matches:
            try:
                hour = int(hour_str)
                minute = int(min_str)
                
                # Validate
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    time_minute = hour * 60 + minute
                    times.append(time_minute)
            except ValueError:
                continue
        
        # Group consecutive times as start-end pairs
        intervals = []
        for i in range(0, len(times) - 1, 2):
            start = times[i]
            end = times[i + 1] if i + 1 < len(times) else times[i]
            if start < end:
                intervals.append((start, end))
        
        return intervals


def extract_times(text: str) -> List[Tuple[int, int]]:
    """Module-level function to extract times from text."""
    wrapper = OCRWrapper()
    return wrapper._extract_times(text)


def extract_days(text: str) -> List[int]:
    """Module-level function to extract days from text."""
    wrapper = OCRWrapper()
    return wrapper._extract_days(text)
