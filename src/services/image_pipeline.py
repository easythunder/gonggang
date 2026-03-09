"""Image processing pipeline: YOLO detection -> OCR -> Coordinate-based extraction."""

import logging
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import io
from PIL import Image

# Lazy import cv2 to avoid libGL dependency issues in headless environments
try:
    import cv2
except ImportError:
    cv2 = None

from src.services.timetable_detector import (
    TimetableDetector,
    CoordinateBasedTimetableProcessor,
    BoundingBox,
    TimetableDetectionError
)
from src.services.ocr import OCRWrapper, OCRFailedError, OCRTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of image processing pipeline."""
    success: bool
    schedule: List[Dict]
    metadata: Dict
    error_message: Optional[str] = None
    
    # Detection details
    detection_bbox: Optional[Dict] = None
    crop_image_bytes: Optional[bytes] = None
    ocr_text: Optional[str] = None
    cell_count: int = 0
    

class TimetableImagePipeline:
    """Complete pipeline: upload -> detect -> crop -> OCR -> extract schedule."""
    
    def __init__(
        self,
        yolo_model_path: Optional[str] = None,
        ocr_timeout: int = 5,
        detection_confidence: float = 0.5
    ):
        """
        Initialize pipeline.
        
        Args:
            yolo_model_path: Path to custom YOLO model
            ocr_timeout: OCR timeout in seconds
            detection_confidence: YOLO detection confidence threshold
        """
        self.detector = TimetableDetector(yolo_model_path)
        self.ocr = OCRWrapper(library="tesseract", timeout_seconds=ocr_timeout)
        self.processor = CoordinateBasedTimetableProcessor()
        self.detection_confidence = detection_confidence
        
        logger.info("TimetableImagePipeline initialized")
    
    def process(
        self,
        image_bytes: bytes,
        display_unit_minutes: int = 30,
        save_crop: bool = False
    ) -> PipelineResult:
        """
        Process image through full pipeline.
        
        Pipeline steps:
        1. Image decoding
        2. YOLO timetable detection
        3. Bounding box extraction
        4. Timetable cropping
        5. OCR text extraction
        6. Coordinate-based schedule generation
        
        Args:
            image_bytes: Raw image bytes
            display_unit_minutes: Display granularity (30, 60, etc.)
            save_crop: Whether to save cropped timetable image
        
        Returns:
            PipelineResult with schedule and metadata
        """
        logger.info("Starting pipeline processing...")
        
        try:
            # Step 1: Decode image
            logger.info("Step 1️⃣: Image decoding")
            image_array = self._decode_image(image_bytes)
            if image_array is None:
                return PipelineResult(
                    success=False,
                    schedule=[],
                    metadata={},
                    error_message="Failed to decode image"
                )
            h, w = image_array.shape[:2]
            logger.info(f"✅ Image decoded: {w}x{h}px")
            
            # Step 2: YOLO Detection
            logger.info("Step 2️⃣: YOLO timetable detection")
            bbox, _ = self.detector.detect_timetable(
                image_bytes,
                confidence_threshold=self.detection_confidence
            )
            
            if bbox is None:
                logger.warning("⚠️ No timetable detected, falling back to full image")
                bbox = BoundingBox(0, 0, w, h, 0.5)
            else:
                logger.info(f"✅ Timetable detected: {bbox}")
            
            # Step 3: Crop timetable
            logger.info("Step 3️⃣: Cropping timetable region")
            crop_array = image_array[bbox.y1:bbox.y2, bbox.x1:bbox.x2]
            logger.info(f"✅ Cropped to {crop_array.shape[1]}x{crop_array.shape[0]}px")
            
            # Save crop if requested
            crop_image_bytes = None
            if save_crop:
                crop_image_bytes = self._cv2_to_bytes(crop_array)
            
            # Step 4: Estimate cell grid
            logger.info("Step 4️⃣: Estimating cell grid")
            num_cols, num_rows = self.processor.estimate_cell_grid(image_array, bbox)
            logger.info(f"✅ Grid estimated: {num_cols}x{num_rows}")
            
            # Step 5: OCR extraction
            logger.info("Step 5️⃣: OCR text extraction")
            try:
                # Convert numpy array to bytes for OCR
                crop_bytes = self._cv2_to_bytes(crop_array)
                ocr_text = self.ocr.parse_image(crop_bytes)
                logger.info(f"✅ OCR completed: {len(ocr_text)} characters")
            except OCRTimeoutError:
                logger.error("❌ OCR timeout")
                return PipelineResult(
                    success=False,
                    schedule=[],
                    metadata={
                        'detection_bbox': bbox.to_dict(),
                        'image_size': (w, h),
                        'cell_grid': (num_cols, num_rows)
                    },
                    error_message="OCR processing timeout",
                    detection_bbox=bbox.to_dict(),
                    crop_image_bytes=crop_image_bytes
                )
            except OCRFailedError as e:
                logger.warning(f"⚠️ OCR failed: {e}")
                ocr_text = ""
            except Exception as e:
                logger.error(f"❌ Unexpected OCR error: {e}")
                return PipelineResult(
                    success=False,
                    schedule=[],
                    metadata={
                        'detection_bbox': bbox.to_dict(),
                        'image_size': (w, h),
                        'cell_grid': (num_cols, num_rows)
                    },
                    error_message=f"OCR error: {str(e)}",
                    detection_bbox=bbox.to_dict(),
                    crop_image_bytes=crop_image_bytes
                )
            
            # Step 6: Detect cells
            logger.info("Step 6️⃣: Cell detection")
            cells = self.detector.detect_cells(image_array, bbox)
            logger.info(f"✅ Detected {len(cells)} cells")
            
            # Step 7: Map OCR to cells
            logger.info("Step 7️⃣: Mapping OCR results to cells")
            ocr_results = self._map_ocr_to_cells(
                ocr_text, crop_array, cells, bbox, num_cols, num_rows
            )
            logger.info(f"✅ Mapped OCR to {len(ocr_results)} cells")
            
            # Step 8: Extract schedule
            logger.info("Step 8️⃣: Extracting schedule from coordinates")
            schedule = self.processor.extract_schedule_from_coordinates(
                image_array, cells, ocr_results
            )
            logger.info(f"✅ Extracted {len(schedule)} schedule entries")
            
            # Success
            return PipelineResult(
                success=True,
                schedule=schedule,
                metadata={
                    'detection_bbox': bbox.to_dict(),
                    'image_size': (w, h),
                    'crop_size': (crop_array.shape[1], crop_array.shape[0]),
                    'cell_grid': (num_cols, num_rows),
                    'ocr_text_length': len(ocr_text),
                    'cell_detections': len(cells),
                    'ocr_cell_mappings': len(ocr_results)
                },
                error_message=None,
                detection_bbox=bbox.to_dict(),
                crop_image_bytes=crop_image_bytes,
                ocr_text=ocr_text,
                cell_count=len(cells)
            )
        
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            return PipelineResult(
                success=False,
                schedule=[],
                metadata={},
                error_message=f"Pipeline error: {str(e)}"
            )
    
    def _decode_image(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Decode image bytes to numpy array."""
        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            img_array = np.array(pil_image)
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            return img_array
        except Exception as e:
            logger.error(f"Image decode error: {e}")
            return None
    
    def _map_ocr_to_cells(
        self,
        ocr_text: str,
        crop_array: np.ndarray,
        cells: List[BoundingBox],
        bbox: BoundingBox,
        num_cols: int,
        num_rows: int
    ) -> Dict[Tuple[int, int], str]:
        """
        Map OCR text to cells using coordinate-based matching.
        
        For now, this is a simplified implementation.
        In production, use more sophisticated OCR spatial analysis.
        """
        ocr_results = {}
        
        # Split OCR text into lines
        lines = ocr_text.strip().split('\n')
        
        # Simple heuristic: map lines to cells based on position
        # This is a placeholder - replace with proper spatial OCR analysis
        for row in range(num_rows):
            for col in range(num_cols):
                cell_idx = row * num_cols + col
                if cell_idx < len(cells):
                    cell = cells[cell_idx]
                    
                    # Check which OCR lines intersect with this cell
                    cell_text = ""
                    for line in lines:
                        # Simple heuristic: if line contains common class name words
                        if any(word in line for word in ['수학', '영어', '과학', '국어', '지리', '역사']):
                            cell_text = line
                            break
                    
                    if cell_text:
                        ocr_results[(row, col)] = cell_text
        
        return ocr_results
    
    @staticmethod
    def _cv2_to_bytes(image_array: np.ndarray) -> bytes:
        """Convert OpenCV image array to PNG bytes."""
        try:
            import cv2
            # Convert BGR to RGB
            rgb_array = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
            
            # Convert to PIL
            pil_image = Image.fromarray(rgb_array)
            
            # Save to bytes
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Image conversion error: {e}")
            return b""
