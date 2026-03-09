"""YOLO-based timetable detection and coordinate-based schedule extraction."""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional
from pathlib import Path
from PIL import Image
import io
import os

# Fix PyTorch 2.6+ weights_only security issue before importing
os.environ['TORCH_ALLOW_UNSAFE_LOAD'] = '1'

# Monkey patch torch.load to disable weights_only before importing YOLO
try:
    import torch
    _original_torch_load = torch.load
    
    def patched_torch_load(*args, **kwargs):
        kwargs['weights_only'] = False
        return _original_torch_load(*args, **kwargs)
    
    torch.load = patched_torch_load
    logger_temp = logging.getLogger(__name__)
    logger_temp.info("PyTorch load patched to disable weights_only")
except ImportError:
    pass

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

logger = logging.getLogger(__name__)


class TimetableDetectionError(Exception):
    """Raised when timetable detection fails."""
    pass


class BoundingBox:
    """Bounding box representation."""
    def __init__(self, x1: int, y1: int, x2: int, y2: int, confidence: float = 0.0):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.width = x2 - x1
        self.height = y2 - y1
        self.confidence = confidence
    
    def to_dict(self) -> Dict:
        return {
            'x1': self.x1, 'y1': self.y1,
            'x2': self.x2, 'y2': self.y2,
            'width': self.width, 'height': self.height,
            'confidence': self.confidence
        }
    
    def __repr__(self):
        return f"BoundingBox(({self.x1},{self.y1})-({self.x2},{self.y2}), conf={self.confidence:.2f})"


class TimetableDetector:
    """YOLO-based timetable detector."""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize YOLO detector.
        
        Args:
            model_path: Path to custom YOLO model. If None, uses YOLOv8n (nano).
        """
        if YOLO is None:
            raise TimetableDetectionError("ultralytics not installed. Install with: pip install ultralytics")
        
        # Workaround for PyTorch 2.6+ weights_only issue
        try:
            import torch
            # Disable weights_only to allow model loading
            import torch.serialization
            torch.serialization.default_weights_only = False
        except (ImportError, AttributeError):
            pass
        
        if model_path:
            if not Path(model_path).exists():
                raise TimetableDetectionError(f"Model file not found: {model_path}")
            self.model = YOLO(model_path)
            logger.info(f"Loaded custom YOLO model: {model_path}")
        else:
            # Use YOLOv8n (nano) - fast and lightweight
            # Will auto-download if not present
            try:
                # Try loading the pre-trained model
                self.model = YOLO("yolov8n.pt")
                logger.info("Loaded YOLOv8n model (nano)")
            except Exception as e:
                # Fallback: use just the architecture (won't have pretrained weights)
                logger.warning(f"Failed to load pretrained YOLOv8n: {e}. Using base architecture...")
                self.model = YOLO("yolov8n.yaml")
                logger.info("Loaded YOLOv8n model from YAML (architecture only)")
    
    def detect_timetable(
        self,
        image_bytes: bytes,
        confidence_threshold: float = 0.5
    ) -> Tuple[Optional[BoundingBox], np.ndarray]:
        """
        Detect timetable region in image.
        
        Args:
            image_bytes: Image bytes
            confidence_threshold: Minimum confidence for detection
        
        Returns:
            Tuple of (bbox, image_array) where bbox is the timetable bounding box
        """
        # Convert bytes to numpy array
        image_array = self._bytes_to_cv2(image_bytes)
        if image_array is None:
            raise TimetableDetectionError("Failed to decode image")
        
        # Run YOLO detection
        results = self.model(image_array, conf=confidence_threshold, verbose=False)
        
        if not results or len(results) == 0:
            logger.warning("No detections found")
            return None, image_array
        
        detections = results[0]
        
        if len(detections.boxes) == 0:
            logger.warning("No bounding boxes detected")
            return None, image_array
        
        # Get highest confidence detection
        best_detection = None
        best_conf = 0
        
        for box in detections.boxes:
            conf = float(box.conf[0])
            if conf > best_conf:
                best_conf = conf
                best_detection = box
        
        if best_detection is None:
            return None, image_array
        
        # Extract bounding box coordinates
        x1, y1, x2, y2 = map(int, best_detection.xyxy[0])
        bbox = BoundingBox(x1, y1, x2, y2, best_conf)
        
        logger.info(f"Detected timetable: {bbox}")
        
        return bbox, image_array
    
    def detect_cells(
        self,
        image_array: np.ndarray,
        bbox: BoundingBox,
        confidence_threshold: float = 0.5
    ) -> List[BoundingBox]:
        """
        Detect individual cells/time slots within timetable.
        
        For now, this uses basic grid detection. In production, 
        use a more sophisticated cell detection model.
        
        Args:
            image_array: Image as numpy array
            bbox: Timetable bounding box
            confidence_threshold: Minimum confidence
        
        Returns:
            List of cell bounding boxes
        """
        import cv2
        
        # Crop to timetable region
        timetable_crop = image_array[bbox.y1:bbox.y2, bbox.x1:bbox.x2]
        
        # Convert to grayscale
        gray = cv2.cvtColor(timetable_crop, cv2.COLOR_BGR2GRAY)
        
        # Get height and width
        h, w = gray.shape
        
        # Estimate cell size (rows and columns)
        # This is a heuristic - adjust based on your timetable format
        # Typically: 7 columns (Mon-Sun), 20-30 rows (30min intervals)
        cell_width = w // 7  # 7 days
        cell_height = h // 24  # 24 hours worth of slots
        
        cells = []
        for row in range(24):
            for col in range(7):
                x1 = col * cell_width
                y1 = row * cell_height
                x2 = (col + 1) * cell_width
                y2 = (row + 1) * cell_height
                
                # Convert to absolute coordinates
                abs_x1 = bbox.x1 + x1
                abs_y1 = bbox.y1 + y1
                abs_x2 = bbox.x1 + x2
                abs_y2 = bbox.y1 + y2
                
                cells.append(BoundingBox(abs_x1, abs_y1, abs_x2, abs_y2))
        
        logger.info(f"Detected {len(cells)} cells in timetable")
        return cells
    
    @staticmethod
    def _bytes_to_cv2(image_bytes: bytes) -> Optional[np.ndarray]:
        """Convert image bytes to OpenCV (BGR) array."""
        try:
            # Load with PIL first
            pil_image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert to numpy array and BGR
            img_array = np.array(pil_image)
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            return img_array
        except Exception as e:
            logger.error(f"Failed to decode image: {e}")
            return None


class CoordinateBasedTimetableProcessor:
    """Extract timetable from coordinates."""
    
    def __init__(self):
        """Initialize processor."""
        self.days = ['월', '화', '수', '목', '금', '토', '일']
        self.hours = list(range(8, 23))  # 08:00 - 22:00
    
    def extract_schedule_from_coordinates(
        self,
        image_array: np.ndarray,
        cells: List[BoundingBox],
        ocr_results: Dict[Tuple[int, int], str]
    ) -> List[Dict]:
        """
        Extract schedule from cell coordinates and OCR results.
        
        Args:
            image_array: Full image
            cells: List of cell bounding boxes
            ocr_results: Dict mapping (row, col) to OCR text
        
        Returns:
            List of schedule entries [{'day': str, 'start': str, 'end': str, ...}]
        """
        h, w = image_array.shape[:2]
        
        schedule = []
        
        # Group cells by day (column)
        for col in range(7):  # Days of week
            col_cells = [cells[row * 7 + col] for row in range(24) if row * 7 + col < len(cells)]
            
            if not col_cells:
                continue
            
            day = self.days[col]
            
            # Group consecutive cells with text
            start_row = None
            
            for row, cell in enumerate(col_cells):
                ocr_text = ocr_results.get((row, col), "").strip()
                
                if ocr_text:  # Cell has content
                    if start_row is None:
                        start_row = row
                else:  # Cell is empty
                    if start_row is not None:
                        # End of a class block
                        start_time = self._row_to_time(start_row)
                        end_time = self._row_to_time(row)
                        
                        # Get class name from OCR results
                        class_name = " ".join(
                            ocr_results.get((r, col), "").strip()
                            for r in range(start_row, row)
                            if ocr_results.get((r, col), "").strip()
                        )
                        
                        if class_name:
                            schedule.append({
                                'day': day,
                                'start': start_time,
                                'end': end_time,
                                'class_name': class_name,
                                'start_row': start_row,
                                'end_row': row,
                                'column': col
                            })
                        
                        start_row = None
            
            # Handle case where class extends to end of day
            if start_row is not None:
                start_time = self._row_to_time(start_row)
                end_time = self._row_to_time(len(col_cells))
                
                class_name = " ".join(
                    ocr_results.get((r, col), "").strip()
                    for r in range(start_row, len(col_cells))
                    if ocr_results.get((r, col), "").strip()
                )
                
                if class_name:
                    schedule.append({
                        'day': day,
                        'start': start_time,
                        'end': end_time,
                        'class_name': class_name,
                        'start_row': start_row,
                        'end_row': len(col_cells),
                        'column': col
                    })
        
        logger.info(f"Extracted {len(schedule)} schedule entries")
        return schedule
    
    @staticmethod
    def _row_to_time(row: int) -> str:
        """Convert row index to time string (HH:MM).
        
        Assumes 24 rows for 8:00-22:00, so each row is 1 hour.
        Adjust multiplier for different granularity (e.g., 0.5 for 30-min slots).
        """
        start_hour = 8
        hours = start_hour + row
        return f"{hours:02d}:00"
    
    def estimate_cell_grid(
        self,
        image_array: np.ndarray,
        bbox: BoundingBox
    ) -> Tuple[int, int]:
        """
        Estimate grid dimensions by analyzing timetable structure.
        
        Args:
            image_array: Full image
            bbox: Timetable bounding box
        
        Returns:
            Tuple of (num_cols, num_rows)
        """
        import cv2
        
        crop = image_array[bbox.y1:bbox.y2, bbox.x1:bbox.x2]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        
        # Detect vertical lines (columns)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=50, maxLineGap=10)
        
        if lines is None:
            return 7, 24  # Default: 7 days, 24 hours
        
        # Count vertical lines (columns)
        vertical_lines = [line for line in lines if abs(line[0][0] - line[0][2]) < 5]
        num_cols = len(vertical_lines) + 1
        
        # Count horizontal lines (rows)
        horizontal_lines = [line for line in lines if abs(line[0][1] - line[0][3]) < 5]
        num_rows = len(horizontal_lines) + 1
        
        logger.info(f"Estimated grid: {num_cols}x{num_rows}")
        return num_cols, num_rows
