"""
Monitoring configuration for the Medical Services Chatbot
"""

from prometheus_client import Counter, Histogram, start_http_server
import time
from typing import Dict, Any
import requests
from functools import wraps

# Define metrics
REQUEST_COUNT = Counter(
    'medical_chatbot_requests_total',
    'Total number of requests processed',
    ['endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'medical_chatbot_request_latency_seconds',
    'Request latency in seconds',
    ['endpoint']
)

ERROR_COUNT = Counter(
    'medical_chatbot_errors_total',
    'Total number of errors',
    ['endpoint', 'error_type']
)

def track_request(endpoint: str):
    """Decorator to track request metrics"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                REQUEST_COUNT.labels(endpoint=endpoint, status='success').inc()
                return result
            except Exception as e:
                REQUEST_COUNT.labels(endpoint=endpoint, status='error').inc()
                ERROR_COUNT.labels(endpoint=endpoint, error_type=type(e).__name__).inc()
                raise
            finally:
                REQUEST_LATENCY.labels(endpoint=endpoint).observe(time.time() - start_time)
        return wrapper
    return decorator

def check_backend_health(api_base_url: str) -> Dict[str, Any]:
    """Check the health of the backend service"""
    try:
        response = requests.get(f"{api_base_url}/health")
        return {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "backend_status": response.status_code,
            "details": response.json() if response.status_code == 200 else None
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

def start_metrics_server(port: int = 8000) -> None:
    """Start the Prometheus metrics server"""
    start_http_server(port) 