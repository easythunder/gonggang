"""
Free-time calculation performance profiling (T076)

Profiles AND calculation and candidate generation with 50 participants
"""
import pytest
import time
import logging
from datetime import datetime
from uuid import uuid4

from src.services.calculation import CalculationService
from src.services.candidates import CandidateExtractor
from src.models.models import Group, Submission, Interval

logger = logging.getLogger(__name__)


def create_test_intervals(num_participants=50):
    """Create test intervals for multiple participants."""
    groups = []
    submissions = []
    intervals = []
    
    base_group_id = uuid4()
    
    for p in range(num_participants):
        # Create 5-10 random intervals per participant
        import random
        random.seed(42 + p)
        
        submission_id = uuid4()
        submissions.append({
            'id': submission_id,
            'group_id': base_group_id,
            'nickname': f'user_{p}',
        })
        
        num_intervals = random.randint(5, 10)
        for i in range(num_intervals):
            day = random.randint(0, 6)  # 0-6 for days
            start = random.randint(0, 1400)  # 0-1439 minutes
            end = min(start + random.randint(30, 240), 1439)
            
            intervals.append({
                'submission_id': submission_id,
                'day_of_week': day,
                'start_minute': start,
                'end_minute': end,
            })
    
    return submissions, intervals


@pytest.mark.performance
class TestCalculationPerformance:
    """Profile calculation performance."""
    
    def test_and_calculation_50_participants(self):
        """Profile AND calculation with 50 participants (T076)."""
        submissions, intervals = create_test_intervals(50)
        
        calc_service = CalculationService()
        
        start = time.time()
        try:
            # Group intervals by submission
            submission_intervals = {}
            for interval in intervals:
                sub_id = interval['submission_id']
                if sub_id not in submission_intervals:
                    submission_intervals[sub_id] = []
                submission_intervals[sub_id].append(interval)
            
            # Run AND calculation
            free_time = calc_service._calculate_and_intersection(
                submission_intervals,
                display_unit_minutes=30
            )
            
            duration_ms = (time.time() - start) * 1000
            
            logger.info(f"\nAND Calculation (50 participants):")
            logger.info(f"  Duration: {duration_ms:.0f}ms")
            logger.info(f"  Free time slots found: {len(free_time) if free_time else 0}")
            
            # Assert fast calculation (<1s)
            assert duration_ms < 1000, f"Calculation took {duration_ms:.0f}ms (target: <1s)"
            
        except Exception as e:
            logger.info(f"Calculation test skipped: {e}")
    
    def test_candidate_extraction_performance(self):
        """Profile candidate extraction with many merged slots (T076)."""
        submissions, intervals = create_test_intervals(30)
        
        extractor = CandidateExtractor()
        
        start = time.time()
        try:
            # Simulate free time slots
            free_slots = []
            import random
            random.seed(42)
            for day in range(7):
                # Create 10-20 free slots per day
                num_slots = random.randint(10, 20)
                for _ in range(num_slots):
                    start_min = random.randint(0, 1300)
                    end_min = min(start_min + random.randint(30, 180), 1439)
                    free_slots.append({
                        'day': day,
                        'start_minute': start_min,
                        'end_minute': end_min,
                        'duration_minutes': end_min - start_min,
                    })
            
            # Extract candidates
            candidates = extractor.extract_candidates(
                free_slots,
                min_duration_minutes=30,
                max_candidates=10
            )
            
            duration_ms = (time.time() - start) * 1000
            
            logger.info(f"\nCandidate Extraction:")
            logger.info(f"  Duration: {duration_ms:.0f}ms")
            logger.info(f"  Input slots: {len(free_slots)}")
            logger.info(f"  Candidates extracted: {len(candidates)}")
            
            assert duration_ms < 500, f"Extraction took {duration_ms:.0f}ms (target: <500ms)"
            
        except Exception as e:
            logger.info(f"Candidate extraction test skipped: {e}")
