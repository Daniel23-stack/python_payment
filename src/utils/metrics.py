"""Metrics and monitoring utilities."""

from prometheus_client import Counter, Histogram, Gauge
from functools import wraps
import time

# Transaction metrics
transactions_total = Counter(
    'transactions_total',
    'Total number of transactions',
    ['type', 'status']
)

transaction_amount = Histogram(
    'transaction_amount',
    'Transaction amounts',
    buckets=[10, 50, 100, 500, 1000, 5000, 10000, 50000]
)

# Account metrics
accounts_total = Gauge(
    'accounts_total',
    'Total number of accounts',
    ['status']
)

# Balance metrics
balance_discrepancy = Counter(
    'balance_discrepancy_total',
    'Number of balance discrepancies detected'
)

# API metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

# Database metrics
db_connections_active = Gauge(
    'db_connections_active',
    'Active database connections'
)

db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0]
)

# Cache metrics
cache_hits_total = Counter('cache_hits_total', 'Total cache hits')
cache_misses_total = Counter('cache_misses_total', 'Total cache misses')


def track_transaction(transaction_type: str, status: str, amount: float = None):
    """Track transaction metrics."""
    transactions_total.labels(type=transaction_type, status=status).inc()
    if amount is not None:
        transaction_amount.observe(amount)


def track_api_request(method: str, endpoint: str, status_code: int, duration: float):
    """Track API request metrics."""
    api_requests_total.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
    api_request_duration.labels(method=method, endpoint=endpoint).observe(duration)


def track_cache_hit():
    """Track cache hit."""
    cache_hits_total.inc()


def track_cache_miss():
    """Track cache miss."""
    cache_misses_total.inc()


def measure_time(func):
    """Decorator to measure function execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start
            # Log or track duration as needed
            pass
    return wrapper

