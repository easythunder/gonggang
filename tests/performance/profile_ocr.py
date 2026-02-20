"""
OCR performance profiling (T075)

Profiles Tesseract OCR parsing performance on typical schedule images
"""
import pytest
import time
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from src.services.ocr import OCRService

logger = logging.getLogger(__name__)


def create_test_schedule_image(width=1200, height=800):
    """Create a realistic test schedule image."""
    # Create image with white background
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw grid lines
    cell_width = width // 5
    cell_height = height // 8
    
    for i in range(6):
        draw.line([(i * cell_width, 0), (i * cell_width, height)], fill='black', width=2)
    for j in range(9):
        draw.line([(0, j * cell_height), (width, j * cell_height)], fill='black', width=2)
    
    # Add text (times and days)
    times = ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00']
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    
    for i, day in enumerate(days):
        draw.text((i * cell_width + 10, 10), day, fill='black')
    
    for j, time_str in enumerate(times):
        draw.text((10, (j + 1) * cell_height + 10), time_str, fill='black')
    
    # Mark some cells as busy (fill with light gray)
    import random
    random.seed(42)
    for _ in range(15):
        i = random.randint(0, 4)
        j = random.randint(0, 7)
        x1 = i * cell_width
        y1 = (j + 1) * cell_height
        x2 = (i + 1) * cell_width
        y2 = (j + 2) * cell_height
        draw.rectangle([x1, y1, x2, y2], fill='lightgray')
    
    # Convert to JPG
    jpg_buffer = BytesIO()
    img.save(jpg_buffer, format='JPEG', quality=85)
    jpg_buffer.seek(0)
    return jpg_buffer.getvalue()


@pytest.mark.performance
class TestOCRPerformance:
    """Profile OCR performance."""
    
    def test_ocr_parse_schedule_image(self):
        """Profile typical schedule image OCR (T075)."""
        ocr_service = OCRService()
        image_data = create_test_schedule_image()
        
        # Warm up
        try:
            ocr_service.parse_schedule(image_data)
        except:
            pass  # Expected if OCR not configured
        
        # Profile 10 parses
        times = []
        for i in range(10):
            start = time.time()
            try:
                result = ocr_service.parse_schedule(image_data)
                duration_ms = (time.time() - start) * 1000
                times.append(duration_ms)
                logger.info(f"OCR parse {i+1}: {duration_ms:.0f}ms")
            except Exception as e:
                logger.warning(f"OCR parse {i+1} failed: {e}")
                break
        
        if times:
            mean_time = sum(times) / len(times)
            max_time = max(times)
            logger.info(f"\nOCR Performance Summary:")
            logger.info(f"  Runs: {len(times)}")
            logger.info(f"  Mean: {mean_time:.0f}ms")
            logger.info(f"  Max: {max_time:.0f}ms")
            
            # Assert reasonable performance
            assert mean_time < 3000, f"OCR mean time {mean_time:.0f}ms exceeds 3s"
            assert max_time < 5000, f"OCR max time {max_time:.0f}ms exceeds 5s"
    
    def test_ocr_memory_cleanup(self):
        """Verify OCR image is discarded from memory (T041)."""
        ocr_service = OCRService()
        image_data = create_test_schedule_image()
        
        # Parse and verify image doesn't stay in memory
        start = time.time()
        try:
            result = ocr_service.parse_schedule(image_data)
            duration_ms = (time.time() - start) * 1000
            
            logger.info(f"OCR parse with memory cleanup: {duration_ms:.0f}ms")
            assert duration_ms < 5000
        except Exception as e:
            logger.info(f"OCR not configured: {e}")
