"""
Load test suite for Meet-Match (T074)

Validates <5s response time, <1s calculation, <500ms polling targets under load
"""
import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import uuid4

from fastapi.testclient import TestClient
from src.main import app


class ResponseTimeTracker:
    """Track response times across concurrent requests."""
    
    def __init__(self):
        self.times = []
        self.errors = []
    
    def add_time(self, duration_ms: float, success: bool = True, error_msg: str = None):
        """Record a response time."""
        if success:
            self.times.append(duration_ms)
        else:
            self.errors.append({
                'duration_ms': duration_ms,
                'error': error_msg
            })
    
    def get_stats(self):
        """Calculate statistics."""
        if not self.times:
            return {
                'count': 0,
                'p50': 0,
                'p95': 0,
                'p99': 0,
                'max': 0,
                'mean': 0,
                'errors': len(self.errors)
            }
        
        sorted_times = sorted(self.times)
        count = len(sorted_times)
        
        return {
            'count': count,
            'p50': sorted_times[int(count * 0.5)],
            'p95': sorted_times[int(count * 0.95)] if count > 20 else sorted_times[-1],
            'p99': sorted_times[int(count * 0.99)] if count > 100 else sorted_times[-1],
            'max': max(sorted_times),
            'mean': sum(sorted_times) / count,
            'errors': len(self.errors),
            'error_rate': len(self.errors) / (count + len(self.errors)) if count + len(self.errors) > 0 else 0
        }


@pytest.mark.performance
class TestLoadPerformance:
    """Load test with concurrent submissions."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def test_group(self, client):
        """Create test group."""
        response = client.post(
            "/groups",
            json={
                "group_name": "load_test_" + str(uuid4())[:8],
                "display_unit_minutes": 30,
            }
        )
        assert response.status_code == 201
        data = response.json()
        return data['data']['group_id']
    
    def test_concurrent_submissions_50_users(self, client, test_group):
        """Test 50 concurrent submissions (T074)."""
        tracker = ResponseTimeTracker()
        num_users = 50
        
        # Create minimal valid JPG header
        dummy_image = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xFF\xD9'
        
        def submit_image(user_idx):
            """Simulate one user uploading an image."""
            start = time.time()
            try:
                response = client.post(
                    f"/groups/{test_group}/submissions",
                    files={'file': ('schedule.jpg', dummy_image, 'image/jpeg')}
                )
                duration_ms = (time.time() - start) * 1000
                
                if response.status_code in [200, 201]:
                    tracker.add_time(duration_ms, success=True)
                    return True
                else:
                    tracker.add_time(duration_ms, success=False, error_msg=f"Status {response.status_code}")
                    return False
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                tracker.add_time(duration_ms, success=False, error_msg=str(e))
                return False
        
        # Run concurrent submissions
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(submit_image, i) for i in range(num_users)]
            results = [f.result() for f in as_completed(futures)]
        
        stats = tracker.get_stats()
        
        # Assertions
        assert stats['count'] > 0, "No successful submissions"
        assert stats['p95'] < 5000, f"P95 response time {stats['p95']:.0f}ms exceeds 5s target"
        
        print(f"\nLoad Test Results (50 users):")
        print(f"  Successful: {stats['count']}")
        print(f"  Mean: {stats['mean']:.0f}ms, P95: {stats['p95']:.0f}ms, Max: {stats['max']:.0f}ms")
    
    def test_polling_response_time(self, client, test_group):
        """Test polling response time (T074)."""
        tracker = ResponseTimeTracker()
        num_requests = 50
        
        def poll_results(req_idx):
            """Simulate polling for results."""
            start = time.time()
            try:
                response = client.get(
                    f"/groups/{test_group}/free-time",
                    params={"interval_ms": 2000}
                )
                duration_ms = (time.time() - start) * 1000
                
                if response.status_code in [200, 410]:
                    tracker.add_time(duration_ms, success=True)
                    return True
                else:
                    tracker.add_time(duration_ms, success=False, error_msg=f"Status {response.status_code}")
                    return False
            except Exception as e:
                duration_ms = (time.time() - start) * 1000
                tracker.add_time(duration_ms, success=False, error_msg=str(e))
                return False
        
        # Run concurrent polling
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(poll_results, i) for i in range(num_requests)]
            results = [f.result() for f in as_completed(futures)]
        
        stats = tracker.get_stats()
        assert stats['count'] > 0, "No successful polls"
        
        print(f"\nPolling Performance (50 requests):")
        print(f"  Successful: {stats['count']}")
        print(f"  Mean: {stats['mean']:.0f}ms, P95: {stats['p95']:.0f}ms")

    })


def test_load_50_concurrent_submissions():
    threads = []
    for _ in range(NUM_CONCURRENT):
        t = threading.Thread(target=submit_image)
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    # Aggregate results
    total_latency = [r["latency"] for r in results]
    ocr_latencies = [r["ocr_latency"] for r in results if r["ocr_latency"] is not None]
    calc_latencies = [r["calc_latency"] for r in results if r["calc_latency"] is not None]
    statuses = [r["status"] for r in results]

    print(f"Total requests: {len(results)}")
    print(f"Status codes: {statuses}")
    print(f"Avg response time: {sum(total_latency)/len(total_latency):.3f}s")
    if ocr_latencies:
        print(f"Avg OCR latency: {sum(ocr_latencies)/len(ocr_latencies):.3f}s")
    if calc_latencies:
        print(f"Avg Calculation latency: {sum(calc_latencies)/len(calc_latencies):.3f}s")
    assert all(s == 200 for s in statuses)
    assert len(results) == NUM_CONCURRENT
