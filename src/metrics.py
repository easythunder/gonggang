"""
Performance metrics and monitoring (T077)

Tracks response times, latencies, and generates performance reports
"""
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime
from statistics import mean, median, stdev
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class RequestMetric:
    """Single request metric."""
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: datetime
    error: Optional[str] = None


class MetricsCollector:
    """Collects and analyzes performance metrics."""
    
    def __init__(self):
        self.metrics: List[RequestMetric] = []
        self._lock = None  # For thread safety if needed
    
    def record(self, endpoint: str, method: str, status_code: int, duration_ms: float, error: str = None):
        """Record a request metric."""
        metric = RequestMetric(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            timestamp=datetime.utcnow(),
            error=error
        )
        self.metrics.append(metric)
    
    def get_percentile(self, percentile: float) -> float:
        """Get percentile of response times."""
        if not self.metrics:
            return 0
        
        durations = [m.duration_ms for m in self.metrics]
        sorted_durations = sorted(durations)
        index = int(len(sorted_durations) * percentile / 100)
        return sorted_durations[min(index, len(sorted_durations) - 1)]
    
    def get_stats(self, endpoint: str = None) -> Dict:
        """Get statistics for endpoint or all."""
        metrics = self.metrics
        if endpoint:
            metrics = [m for m in metrics if m.endpoint == endpoint]
        
        if not metrics:
            return {
                'count': 0,
                'errors': 0,
                'mean_ms': 0,
                'median_ms': 0,
                'stdev_ms': 0,
                'p95_ms': 0,
                'p99_ms': 0,
                'max_ms': 0,
                'min_ms': 0
            }
        
        durations = [m.duration_ms for m in metrics]
        errors = len([m for m in metrics if m.error])
        
        stats = {
            'count': len(metrics),
            'errors': errors,
            'error_rate': errors / len(metrics) if metrics else 0,
            'mean_ms': mean(durations),
            'median_ms': median(durations),
            'max_ms': max(durations),
            'min_ms': min(durations),
            'p95_ms': sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations),
            'p99_ms': sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 100 else max(durations),
        }
        
        if len(durations) > 1:
            stats['stdev_ms'] = stdev(durations)
        else:
            stats['stdev_ms'] = 0
        
        return stats
    
    def get_endpoints_stats(self) -> Dict[str, Dict]:
        """Get stats for each endpoint."""
        endpoints = set(m.endpoint for m in self.metrics)
        return {ep: self.get_stats(ep) for ep in endpoints}
    
    def print_report(self):
        """Print performance report."""
        if not self.metrics:
            logger.info("No metrics collected")
            return
        
        overall_stats = self.get_stats()
        endpoints_stats = self.get_endpoints_stats()
        
        logger.info("\n" + "="*60)
        logger.info("PERFORMANCE REPORT")
        logger.info("="*60)
        
        logger.info(f"\nOverall Statistics:")
        logger.info(f"  Total Requests: {overall_stats['count']}")
        logger.info(f"  Errors: {overall_stats['errors']} ({overall_stats['error_rate']*100:.1f}%)")
        logger.info(f"  Mean:   {overall_stats['mean_ms']:.1f}ms")
        logger.info(f"  Median: {overall_stats['median_ms']:.1f}ms")
        logger.info(f"  Stdev:  {overall_stats['stdev_ms']:.1f}ms")
        logger.info(f"  P95:    {overall_stats['p95_ms']:.1f}ms")
        logger.info(f"  P99:    {overall_stats['p99_ms']:.1f}ms")
        logger.info(f"  Max:    {overall_stats['max_ms']:.1f}ms")
        
        logger.info(f"\nBy Endpoint:")
        for endpoint, stats in endpoints_stats.items():
            logger.info(f"\n  {endpoint}")
            logger.info(f"    Count: {stats['count']}, Mean: {stats['mean_ms']:.1f}ms, P95: {stats['p95_ms']:.1f}ms")


# Global metrics collector
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector."""
    return _metrics_collector


def record_metric(endpoint: str, method: str, status_code: int, duration_ms: float, error: str = None):
    """Record a metric."""
    _metrics_collector.record(endpoint, method, status_code, duration_ms, error)


class MetricsMiddleware:
    """Middleware to track request metrics."""
    
    def __init__(self, app):
        self.app = app
    
    def __call__(self, scope):
        """ASGI app."""
        async def asgi(receive, send):
            start = time.time()
            
            async def send_with_metrics(message):
                if message['type'] == 'http.response.start':
                    duration_ms = (time.time() - start) * 1000
                    status_code = message['status']
                    endpoint = scope.get('path', 'unknown')
                    method = scope.get('method', 'unknown')
                    record_metric(endpoint, method, status_code, duration_ms)
                
                await send(message)
            
            await self.app(scope, receive, send_with_metrics)
        
        return asgi
