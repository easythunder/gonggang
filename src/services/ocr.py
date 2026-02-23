"""Enhanced OCR service for Everytime schedule images.

Features:
- Korean language support
- Image preprocessing (brightness, contrast, rotation detection)
- Everytime-specific schedule parsing
- Training dataset integration
"""
import logging
import re
from io import BytesIO
from typing import List, Tuple, Optional, Dict, Any
from PIL import Image, ImageOps, ImageEnhance
import pytesseract

logger = logging.getLogger(__name__)


class OCRTimeoutError(Exception):
    """Raised when OCR parsing times out."""
    pass


class OCRFailedError(Exception):
    """Raised when OCR parsing fails."""
    pass


class EverytimeScheduleParser:
    """Parser specific to Everytime schedule images."""
    
    # Everytime-specific keywords (Korean + English)
    EVERYTIME_KEYWORDS = {
        # Korean
        '월': 'MONDAY',
        '화': 'TUESDAY', 
        '수': 'WEDNESDAY',
        '목': 'THURSDAY',
        '금': 'FRIDAY',
        '토': 'SATURDAY',
        '일': 'SUNDAY',
        # English (full and abbreviated)
        'monday': 'MONDAY', 'mon': 'MONDAY',
        'tuesday': 'TUESDAY', 'tue': 'TUESDAY', 'tues': 'TUESDAY',
        'wednesday': 'WEDNESDAY', 'wed': 'WEDNESDAY',
        'thursday': 'THURSDAY', 'thu': 'THURSDAY', 'thurs': 'THURSDAY',
        'friday': 'FRIDAY', 'fri': 'FRIDAY',
        'saturday': 'SATURDAY', 'sat': 'SATURDAY',
        'sunday': 'SUNDAY', 'sun': 'SUNDAY',
    }
    
    # Time patterns
    TIME_PATTERN_KOR = r'(\d{1,2}):(\d{2})'  # HH:MM format
    TIME_RANGE_PATTERN = r'(\d{1,2}):(\d{2})\s*[-~]\s*(\d{1,2}):(\d{2})'  # HH:MM-HH:MM format
    
    def parse(self, text: str) -> List[Dict[str, Any]]:
        """Parse OCR text and extract schedule entries.
        
        Args:
            text: Raw OCR text
        
        Returns:
            List of schedule entries with day, start, end times
        """
        entries = []
        
        # Split by lines
        lines = text.split('\n')
        
        current_day = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for day name (Korean or English)
            line_lower = line.lower()
            for day_keyword, eng_day in self.EVERYTIME_KEYWORDS.items():
                # For Korean characters, check as-is
                # For English, check lowercase version
                check_against = line_lower if day_keyword.islower() else line
                if day_keyword in check_against:
                    current_day = eng_day
                    break
            
            # Extract times from this line (supports both HH:MM-HH:MM and individual times)
            times = self._extract_times_from_line(line)
            
            if current_day and times:
                for start, end in times:
                    entries.append({
                        'day': current_day,
                        'start': start,
                        'end': end,
                        'raw_text': line
                    })
        
        return entries
    
    def _extract_times_from_line(self, line: str) -> List[Tuple[str, str]]:
        """Extract time pairs from a line.
        
        Supports formats:
        - HH:MM-HH:MM (e.g., "9:00-10:30")
        - Individual times (e.g., "9:00 10:30")
        
        Args:
            line: A single line of text
        
        Returns:
            List of (start_time, end_time) tuples in HH:MM format
        """
        times = []
        
        # First, try to match time ranges (HH:MM-HH:MM)
        range_matches = re.findall(self.TIME_RANGE_PATTERN, line)
        for match in range_matches:
            start_h, start_m, end_h, end_m = match
            start_time = f"{start_h.zfill(2)}:{start_m}"
            end_time = f"{end_h.zfill(2)}:{end_m}"
            times.append((start_time, end_time))
        
        # If no range matches found, try individual time extraction
        if not times:
            matches = re.findall(self.TIME_PATTERN_KOR, line)
            time_strs = [f"{h.zfill(2)}:{m}" for h, m in matches]
            
            # Group consecutive time pairs
            for i in range(0, len(time_strs) - 1, 2):
                start = time_strs[i]
                end = time_strs[i + 1]
                times.append((start, end))
        
        return times


class OCRWrapper:
    """Enhanced OCR wrapper with preprocessing and Everytime support."""

    def __init__(self, library: str = "tesseract", timeout_seconds: int = 5):
        """Initialize enhanced OCR wrapper.
        
        Args:
            library: 'tesseract' (or 'paddleocr' in future)
            timeout_seconds: Timeout for OCR operation
        """
        self.library = library
        self.timeout_seconds = timeout_seconds
        self.schedule_parser = EverytimeScheduleParser()
        logger.info(f"Initialized enhanced OCR: {library} ({timeout_seconds}s timeout)")

    def parse_image(self, image_bytes: bytes) -> str:
        """Parse an image with preprocessing and extract text.
        
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

        image_stream = BytesIO(image_bytes)
        
        try:
            # Load image from bytes
            image = Image.open(image_stream)
            
            # Validate image
            if image.size == (0, 0):
                logger.warning("Image has zero size")
                raise OCRFailedError("Invalid image dimensions")

            logger.debug(f"Parsing image: {image.size} {image.format}")
            
            # Preprocess image
            processed_image = self._preprocess_image(image)
            
            # Extract text with enhanced language support
            if self.library == "tesseract":
                text = self._parse_with_tesseract(processed_image)
            else:
                raise ValueError(f"Unsupported OCR library: {self.library}")

            logger.info(f"OCR successful: {len(text)} chars extracted")
            return text

        except Image.UnidentifiedImageError:
            logger.error("Invalid image format")
            raise OCRFailedError("Invalid image format - cannot identify")
        except (OCRTimeoutError, OCRFailedError):
            raise
        except Exception as e:
            logger.error(f"OCR parsing failed: {e}", exc_info=True)
            raise OCRFailedError(f"OCR parsing failed: {str(e)}")
        finally:
            image_stream.close()

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR accuracy.
        
        Applies:
        - RGB to grayscale conversion
        - Contrast enhancement (1.5x)
        - Brightness normalization
        - Sharpening (2.0x)
        - Auto-level normalization
        
        Args:
            image: PIL Image object
        
        Returns:
            Processed image
        """
        # Convert to grayscale for better OCR
        if image.mode != 'L':
            image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # Enhance brightness
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.1)
        
        # Sharpen
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        # Auto-level (normalize) for better contrast
        image = ImageOps.autocontrast(image, cutoff=0)
        
        logger.debug("Image preprocessing completed")
        return image

    def _parse_with_tesseract(self, image: Image.Image) -> str:
        """Parse image with Tesseract OCR.
        
        Supports Korean language by using 'kor' language model.
        Falls back to English if Korean detection fails.
        
        Args:
            image: PIL Image object
        
        Returns:
            Extracted text
        
        Raises:
            OCRFailedError: If OCR fails
        """
        try:
            # Try Korean language support first
            # This requires Korean language data in Tesseract
            try:
                text = pytesseract.image_to_string(image, lang='kor+eng')
                logger.debug("OCR with Korean language model")
            except Exception as e:
                # Fallback to English only
                logger.warning(f"Korean language model not available: {e}, using English only")
                text = pytesseract.image_to_string(image, lang='eng')
            
            if not text or not text.strip():
                logger.warning("OCR produced empty result")
            
            return text

        except Exception as e:
            logger.error(f"Tesseract error: {e}")
            raise OCRFailedError(f"Tesseract error: {e}")

    def parse_schedule(self, image_bytes: bytes) -> Dict[str, Any]:
        """Parse image and extract schedule data.
        
        Args:
            image_bytes: Image file content as bytes
        
        Returns:
            Dictionary with:
            - raw_text: Raw OCR text
            - schedule: List of parsed schedule entries
            - confidence: Confidence score (0-1)
        
        Raises:
            OCRFailedError: If parsing fails
        """
        # Extract text
        raw_text = self.parse_image(image_bytes)
        
        # Parse schedule from text
        schedule = self.schedule_parser.parse(raw_text)
        
        # Calculate confidence based on number of entries found
        confidence = min(1.0, len(schedule) / 10.0) if schedule else 0.0
        
        logger.info(f"Extracted {len(schedule)} schedule entries with {confidence:.1%} confidence")
        
        return {
            'raw_text': raw_text,
            'schedule': schedule,
            'confidence': confidence,
            'parser': 'everytime'
        }

    def parse_schedule_text(self, ocr_text: str) -> List[Tuple[int, int, int]]:
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

        schedule = self.schedule_parser.parse(ocr_text)
        intervals = []
        
        days_map = {
            'MONDAY': 0, 'TUESDAY': 1, 'WEDNESDAY': 2,
            'THURSDAY': 3, 'FRIDAY': 4, 'SATURDAY': 5, 'SUNDAY': 6
        }
        
        for entry in schedule:
            day_name = entry.get('day')
            start_time = entry.get('start')
            end_time = entry.get('end')
            
            if not all([day_name, start_time, end_time]):
                continue
            
            day_num = days_map.get(day_name)
            if day_num is None:
                continue
            
            try:
                # Parse times HH:MM -> minutes since midnight
                start_h, start_m = map(int, start_time.split(':'))
                end_h, end_m = map(int, end_time.split(':'))
                
                start_minute = start_h * 60 + start_m
                end_minute = end_h * 60 + end_m
                
                if 0 <= start_minute < end_minute <= 1440:
                    intervals.append((day_num, start_minute, end_minute))
            except (ValueError, IndexError):
                continue
        
        # Fallback: If no day-based schedule found, try extracting times from the text
        # and apply them to all weekdays
        if not intervals:
            time_intervals = self._extract_times(ocr_text)
            if time_intervals:
                # Apply extracted times to all weekdays (0-6: Monday-Sunday)
                for day_num in range(7):
                    for start_min, end_min in time_intervals:
                        if 0 <= start_min < end_min <= 1440:
                            intervals.append((day_num, start_min, end_min))
                logger.debug(f"Fallback: Applied {len(time_intervals)} time intervals to all {len(intervals)} day slots")
        
        logger.info(f"Extracted {len(intervals)} schedule intervals from OCR text")
        return intervals

    def extract_intervals(self, text: str) -> List[Tuple[int, int, int]]:
        """Extract time intervals (day, start, end) from text."""
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
            '월': 0, '화': 1, '수': 2, '목': 3,
            '금': 4, '토': 5, '일': 6,
        }
        
        found_days = set()
        text_lower = text.lower()
        
        for day_name, day_num in days_map.items():
            if day_name in text_lower:
                found_days.add(day_num)
        
        return sorted(list(found_days))

    def _extract_times(self, text: str) -> List[Tuple[int, int]]:
        """Extract time intervals as minutes from midnight.
        
        Returns list of (start_minute, end_minute) tuples.
        For example: 14:30 to 15:45 → (870, 945)
        
        Note: This function is primarily for internal use.
        Use parse_schedule_text() for full schedule parsing.
        """
        # Pattern: HH:MM or H:MM
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


# Backward compatibility alias
class OCRService:
    """Alias for OCRWrapper for backward compatibility."""
    def __init__(self):
        self.wrapper = OCRWrapper()
    
    def parse_image(self, image_bytes: bytes) -> str:
        return self.wrapper.parse_image(image_bytes)
    
    def parse_schedule(self, image_bytes: bytes) -> Dict[str, Any]:
        return self.wrapper.parse_schedule(image_bytes)
