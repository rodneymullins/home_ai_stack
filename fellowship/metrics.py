#!/usr/bin/env python3
"""
Fellowship Metrics - Prometheus metrics export
Exposes metrics on port 9090 for scraping by Prometheus.
"""

from prometheus_client import Counter, Histogram, Gauge, start_http_server
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FellowshipMetrics:
    """Manages Prometheus metrics for The Fellowship."""
    
    def __init__(self, port=9090):
        self.port = port
        
        # Metrics Definitions
        
        # Request counters
        self.requests_total = Counter(
            'fellowship_requests_total',
            'Total AI requests processed',
            ['endpoint', 'model', 'status']
        )
        
        # Response time histogram
        self.response_time = Histogram(
            'fellowship_response_time_seconds',
            'Time taken to generate response',
            ['endpoint', 'model']
        )
        
        # Endpoint health status (0=Down, 1=Up)
        self.endpoint_up = Gauge(
            'fellowship_endpoint_up',
            'Current health status of endpoint',
            ['endpoint']
        )
        
        # Failover events
        self.failovers_total = Counter(
            'fellowship_failovers_total',
            'Total failover events occurred',
            ['from_endpoint', 'to_endpoint']
        )
        
        # Cache stats
        self.cache_hits = Counter(
            'fellowship_cache_hits_total',
            'Total cache hits'
        )
        self.cache_misses = Counter(
            'fellowship_cache_misses_total',
            'Total cache misses'
        )
        
        try:
            start_http_server(self.port)
            logger.info(f"✅ Metrics server started on port {self.port}")
        except Exception as e:
            logger.warning(f"⚠️  Metrics server failed to start (port in use?): {e}")

    def record_request(self, endpoint, model, status, duration_seconds):
        """Record a completed request."""
        self.requests_total.labels(
            endpoint=endpoint,
            model=model,
            status=status
        ).inc()
        
        self.response_time.labels(
            endpoint=endpoint,
            model=model
        ).observe(duration_seconds)
    
    def update_health(self, endpoint, is_healthy):
        """Update endpoint health status."""
        self.endpoint_up.labels(
            endpoint=endpoint
        ).set(1 if is_healthy else 0)
    
    def record_failover(self, from_eps, to_eps):
        """Record a failover event."""
        self.failovers_total.labels(
            from_endpoint=from_eps,
            to_endpoint=to_eps
        ).inc()
    
    def record_cache(self, hit=True):
        """Record cache hit/miss."""
        if hit:
            self.cache_hits.inc()
        else:
            self.cache_misses.inc()


# Global instance
_metrics_instance = None

def get_metrics(port=9090):
    """Get singleton metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = FellowshipMetrics(port)
    return _metrics_instance


if __name__ == '__main__':
    print(f"📊 Starting Metrics Server on port 9090...")
    m = get_metrics()
    import time
    while True:
        time.sleep(1)
