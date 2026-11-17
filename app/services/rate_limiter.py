"""
CampusAssist: In-Memory Sliding-Window Rate Limiter.
Mitigates brute-force credential stuffing and API denial-of-service (CWE-307 / CWE-770)
using a thread-safe sliding window tracking client IPs.
"""

import time
import threading
from collections import defaultdict
from functools import wraps
from typing import Dict, List, Tuple
from flask import request, jsonify, current_app, Response


class InMemoryRateLimiter:
    """Thread-safe sliding-window rate limiter."""

    def __init__(self):
        self._lock = threading.Lock()
        # Maps (client_key, endpoint_key) -> list of timestamp floats
        self._history: Dict[Tuple[str, str], List[float]] = defaultdict(list)

    def is_allowed(self, client_key: str, endpoint_key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Evaluates whether a request from client_key for endpoint_key is permitted.
        Returns: (is_allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            key = (client_key, endpoint_key)
            timestamps = self._history[key]

            # Prune records older than window_start
            valid_timestamps = [t for t in timestamps if t > window_start]

            if len(valid_timestamps) >= limit:
                # Calculate remaining time until oldest request leaves the window
                oldest = valid_timestamps[0]
                retry_after = max(1, int(oldest + window_seconds - now))
                self._history[key] = valid_timestamps
                return False, retry_after

            # Record current request
            valid_timestamps.append(now)
            self._history[key] = valid_timestamps
            return True, 0

    def reset(self):
        """Clear all rate limit state (useful in test teardowns)."""
        with self._lock:
            self._history.clear()


# Global limiter instance
_global_limiter = InMemoryRateLimiter()


def get_rate_limiter() -> InMemoryRateLimiter:
    return _global_limiter


def get_client_ip() -> str:
    """Extracts client IP, respecting proxy headers if behind trusted gateway."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first untrusted client IP in the chain
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def rate_limit(limit: int = 30, window_seconds: int = 60, key_prefix: str = ""):
    """
    Decorator to enforce rate limiting on Flask routes.
    Disabled when RATELIMIT_ENABLED is False or in TESTING mode unless explicitly enabled.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check config toggles
            enabled = current_app.config.get("RATELIMIT_ENABLED", True) or current_app.config.get("TESTING_RATELIMIT_ACTIVE", False)
            if not enabled:
                return f(*args, **kwargs)

            # Skip during general testing unless explicitly overridden
            if current_app.config.get("TESTING") and not current_app.config.get("TESTING_RATELIMIT_ACTIVE"):
                return f(*args, **kwargs)

            endpoint_key = key_prefix or request.endpoint or request.path
            client_ip = get_client_ip()

            allowed, retry_after = _global_limiter.is_allowed(
                client_key=client_ip,
                endpoint_key=endpoint_key,
                limit=limit,
                window_seconds=window_seconds,
            )

            if not allowed:
                # Return JSON 429 for APIs or if client accepts JSON
                if request.path.startswith("/api/") or request.is_json:
                    resp = jsonify({
                        "error": "Too Many Requests",
                        "message": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                        "retry_after": retry_after,
                    })
                    resp.status_code = 429
                    resp.headers["Retry-After"] = str(retry_after)
                    return resp
                else:
                    return Response(
                        f"<h1>429 Too Many Requests</h1><p>Rate limit exceeded. Please try again in {retry_after} seconds.</p>",
                        status=429,
                        headers={"Retry-After": str(retry_after), "Content-Type": "text/html"},
                    )

            return f(*args, **kwargs)
        return decorated_function
    return decorator
