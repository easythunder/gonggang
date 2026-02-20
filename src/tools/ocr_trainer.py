"""OCR Trainer - Learn and improve from real Everytime schedule images.

This tool helps evaluate OCR accuracy on real Everytime schedule images
and iteratively improve the extraction logic.
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from io import BytesIO
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


@dataclass
class ScheduleEntry:
    """A single schedule entry."""
    day: str
    start: str
    end: str
    class_name: str = ""


@dataclass
class AnnotationData:
    """Annotation data for a single image."""
    image_file: str
    extracted_text: str
    schedule: List[Dict[str, str]]
    notes: str = ""
    difficulty: str = "medium"


class OCRTrainer:
    """Train and evaluate OCR on real Everytime images."""

    def __init__(self, data_dir: Path = None):
        """Initialize OCR trainer.
        
        Args:
            data_dir: Path to data/everytime_samples directory
        """
        if data_dir is None:
            # Default to src/../data/everytime_samples
            data_dir = Path(__file__).parent.parent.parent / "data" / "everytime_samples"
        
        self.data_dir = data_dir
        self.images_dir = data_dir / "images"
        self.annotations_dir = data_dir / "annotations"
        self.results_dir = data_dir / "results"
        
        # Create directories if they don't exist
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.annotations_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"OCR Trainer initialized: {self.data_dir}")

    def process_image(self, image_path: Path) -> str:
        """Extract text from image using Tesseract.
        
        Args:
            image_path: Path to image file
        
        Returns:
            Extracted text
        """
        try:
            # Load image
            with Image.open(image_path) as img:
                # Preprocess image for better OCR (optional)
                # - Increase brightness/contrast
                # - Resize if too small
                # - Convert to grayscale for better OCR accuracy
                
                text = pytesseract.image_to_string(img, lang="eng+kor")
                logger.info(f"Extracted {len(text)} chars from {image_path.name}")
                return text
        except Exception as e:
            logger.error(f"Failed to process {image_path}: {e}")
            return ""

    def load_annotation(self, annotation_path: Path) -> AnnotationData:
        """Load annotation data from JSON file.
        
        Args:
            annotation_path: Path to annotation JSON file
        
        Returns:
            AnnotationData object
        """
        try:
            with open(annotation_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to AnnotationData
            schedule = [ScheduleEntry(**entry) for entry in data.get('schedule', [])]
            return AnnotationData(
                image_file=data.get('image_file'),
                extracted_text=data.get('extracted_text'),
                schedule=data.get('schedule', []),
                notes=data.get('notes', ''),
                difficulty=data.get('difficulty', 'medium')
            )
        except Exception as e:
            logger.error(f"Failed to load annotation {annotation_path}: {e}")
            return None

    def evaluate_single(self, image_path: Path, annotation_path: Path) -> Dict[str, Any]:
        """Evaluate OCR on a single image.
        
        Args:
            image_path: Path to image
            annotation_path: Path to annotation
        
        Returns:
            Evaluation result with metrics
        """
        # Load annotation (ground truth)
        annotation = self.load_annotation(annotation_path)
        if not annotation:
            return None

        # Extract text using OCR
        ocr_text = self.process_image(image_path)

        # Compare with ground truth
        ground_truth_text = annotation.extracted_text
        
        # Simple metrics
        ocr_lines = set(ocr_text.lower().strip().split('\n'))
        truth_lines = set(ground_truth_text.lower().strip().split('\n'))
        
        # Calculate Jaccard similarity
        intersection = len(ocr_lines & truth_lines)
        union = len(ocr_lines | truth_lines)
        similarity = intersection / union if union > 0 else 0.0

        # Check schedule extraction
        extracted_schedule = self._parse_schedule_from_text(ocr_text)
        expected_schedule = annotation.schedule
        
        schedule_accuracy = self._calculate_schedule_accuracy(
            extracted_schedule, 
            expected_schedule
        )

        result = {
            'image_file': image_path.name,
            'annotation_file': annotation_path.name,
            'difficulty': annotation.difficulty,
            'notes': annotation.notes,
            'ocr_text': ocr_text,
            'ground_truth_text': ground_truth_text,
            'text_similarity': round(similarity, 3),
            'schedule_accuracy': round(schedule_accuracy, 3),
            'extracted_count': len(extracted_schedule),
            'expected_count': len(expected_schedule),
        }

        return result

    def evaluate_all(self) -> Dict[str, Any]:
        """Evaluate OCR on all images with annotations.
        
        Returns:
            Summary report with all results
        """
        results = []
        
        # Find all annotation files
        annotation_files = sorted(self.annotations_dir.glob('*.json'))
        
        if not annotation_files:
            logger.warning("No annotation files found")
            return {'results': [], 'summary': {}}

        for annotation_path in annotation_files:
            # Find corresponding image
            image_name = annotation_path.stem  # Remove .json
            image_path = None
            
            for ext in ['jpg', 'jpeg', 'png', 'gif']:
                candidate = self.images_dir / f"{image_name}.{ext}"
                if candidate.exists():
                    image_path = candidate
                    break
            
            if not image_path:
                logger.warning(f"No image found for {annotation_path.name}")
                continue

            # Evaluate
            result = self.evaluate_single(image_path, annotation_path)
            if result:
                results.append(result)

        # Calculate summary
        summary = self._calculate_summary(results)

        return {
            'results': results,
            'summary': summary,
            'total_images': len(results)
        }

    def _parse_schedule_from_text(self, text: str) -> List[Dict[str, str]]:
        """Parse schedule from OCR text.
        
        Args:
            text: Raw OCR text
        
        Returns:
            List of schedule entries
        """
        # This is a simplified parser
        # In practice, you'd implement more sophisticated parsing
        import re
        
        entries = []
        
        # Look for patterns like "Monday 9:00-11:00"
        pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        for match in matches:
            day, start_h, start_m, end_h, end_m = match.groups()
            entries.append({
                'day': day.upper(),
                'start': f"{start_h}:{start_m}",
                'end': f"{end_h}:{end_m}"
            })
        
        return entries

    def _calculate_schedule_accuracy(self, extracted: List, expected: List) -> float:
        """Calculate schedule extraction accuracy.
        
        Args:
            extracted: Extracted schedule entries
            expected: Expected schedule entries
        
        Returns:
            Accuracy score (0-1)
        """
        if not expected:
            return 1.0 if not extracted else 0.0

        if not extracted:
            return 0.0

        # Simple count-based accuracy
        # In practice, you'd use more sophisticated matching
        matches = 0
        for exp in expected:
            for ext in extracted:
                if ext.get('day') == exp.get('day') and \
                   ext.get('start') == exp.get('start') and \
                   ext.get('end') == exp.get('end'):
                    matches += 1
                    break

        return matches / len(expected)

    def _calculate_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics.
        
        Args:
            results: List of evaluation results
        
        Returns:
            Summary statistics
        """
        if not results:
            return {}

        text_similarities = [r['text_similarity'] for r in results]
        schedule_accuracies = [r['schedule_accuracy'] for r in results]

        return {
            'avg_text_similarity': round(sum(text_similarities) / len(text_similarities), 3),
            'avg_schedule_accuracy': round(sum(schedule_accuracies) / len(schedule_accuracies), 3),
            'min_text_similarity': round(min(text_similarities), 3),
            'max_text_similarity': round(max(text_similarities), 3),
            'min_schedule_accuracy': round(min(schedule_accuracies), 3),
            'max_schedule_accuracy': round(max(schedule_accuracies), 3),
        }

    def generate_report(self) -> None:
        """Generate evaluation report and save results."""
        logger.info("Evaluating all images...")
        
        evaluation = self.evaluate_all()
        
        # Save results
        results_file = self.results_dir / 'ocr_evaluation.json'
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(evaluation, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {results_file}")

        # Print summary
        summary = evaluation['summary']
        print("\n" + "="*60)
        print("OCR Evaluation Report")
        print("="*60)
        print(f"Total images evaluated: {evaluation['total_images']}")
        print(f"\nText Extraction:")
        print(f"  Average similarity: {summary.get('avg_text_similarity', 'N/A')}")
        print(f"  Range: {summary.get('min_text_similarity')} - {summary.get('max_text_similarity')}")
        print(f"\nSchedule Extraction:")
        print(f"  Average accuracy: {summary.get('avg_schedule_accuracy', 'N/A')}")
        print(f"  Range: {summary.get('min_schedule_accuracy')} - {summary.get('max_schedule_accuracy')}")
        print("="*60 + "\n")

        # Print per-image results
        print("Per-Image Results:")
        print("-"*60)
        for result in evaluation['results']:
            print(f"\n{result['image_file']} ({result['difficulty']})")
            print(f"  Text Similarity: {result['text_similarity']}")
            print(f"  Schedule Accuracy: {result['schedule_accuracy']}")
            print(f"  Schedules: {result['extracted_count']}/{result['expected_count']}")


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='OCR Trainer for Everytime schedules')
    parser.add_argument('command', choices=['evaluate', 'report'], help='Command to run')
    
    args = parser.parse_args()
    
    trainer = OCRTrainer()
    
    if args.command == 'evaluate':
        trainer.generate_report()
    elif args.command == 'report':
        trainer.generate_report()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()
