"""
Configurable rate limiting middleware with pluggable backends.

Supports in-memory (single process) and Redis (distributed) storage.
Applies per-endpoint limits via before_request / after_request hooks
and attaches standard X-RateLimit-* headers to every API response.
"""

import abc
import threading
import time
from typing import Optional, Tuple

from flask import Flask, request, jsonify, g


# ---------------------------------------------------------------------------
# Backend interface
# ---------------------------------------------------------------------------

class RateLimitBackend(abc.ABC):
    """Abstract backend for storing rate-limit counters."""

    @abc.abstractmethod
    def hit(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int, int]:
        """
        Record a request and check whether the client is over the limit.

        Returns:
            (is_limited, remaining, reset_timestamp)
        """

    @abc.abstractmethod
    def reset(self, key: str) -> None:
        """Remove all recorded hits for *key* (useful in tests)."""

    @abc.abstractmethod
    def clear_all(self) -> None:
        """Wipe every key (useful in tests)."""


# ---------------------------------------------------------------------------
# In-memory backend  (single-process, zero dependencies)
# ---------------------------------------------------------------------------

class MemoryBackend(RateLimitBackend):
    """Thread-safe sliding-window counter stored in a plain dict."""

    def __init__(self) -> None:
        self._requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int, int]:
        now = time.time()
        cutoff = now - window_seconds
        reset_at = int(now + window_seconds)

        with self._lock:
            timestamps = self._requests.get(key, [])
            # prune expired entries
            timestamps = [t for t in timestamps if t > cutoff]

            if len(timestamps) >= max_requests:
                self._requests[key] = timestamps
                return True, 0, reset_at

            timestamps.append(now)
            self._requests[key] = timestamps
            remaining = max(0, max_requests - len(timestamps))
            return False, remaining, reset_at

    def reset(self, key: str) -> None:
        with self._lock:
            self._requests.pop(key, None)

    def clear_all(self) -> None:
        with self._lock:
            self._requests.clear()


# ---------------------------------------------------------------------------
# Redis backend  (distributed, requires redis-py)
# ---------------------------------------------------------------------------

class RedisBackend(RateLimitBackend):
    """Sliding-window counter backed by a Redis sorted set."""

    def __init__(self, redis_url: str) -> None:
        import redis
        self._redis = redis.from_url(redis_url)

    def hit(self, key: str, max_requests: int, window_seconds: int) -> Tuple[bool, int, int]:
        now = time.time()
        cutoff = now - window_seconds
        reset_at = int(now + window_seconds)
        pipe = self._redis.pipeline(True)
        try:
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, window_seconds)
            results = pipe.execute()
        except Exception:
            # If Redis is down, fail open (allow the request)
            return False, max_requests, reset_at

        current_count = results[1]  # zcard result before the zadd
        if current_count >= max_requests:
            return True, 0, reset_at

        remaining = max(0, max_requests - (current_count + 1))
        return False, remaining, reset_at

    def reset(self, key: str) -> None:
        self._redis.delete(key)

    def clear_all(self) -> None:
        # Only clear rate-limit keys (prefixed with "rl:")
        for batch_key in self._redis.scan_iter("rl:*"):
            self._redis.delete(batch_key)


# ---------------------------------------------------------------------------
# Public API — initialise on the Flask app
# ---------------------------------------------------------------------------

# Module-level reference so tests / decorators can access the active backend.
_backend: Optional[RateLimitBackend] = None


def get_backend() -> Optional[RateLimitBackend]:
    """Return the active rate-limit backend (or *None* if not initialised)."""
    return _backend


def init_rate_limiting(app: Flask) -> None:
    """
    Read config and wire up before_request / after_request hooks.

    Relevant config keys (set in Config / env):
        RATE_LIMIT_ENABLED       bool   – master switch (default True)
        RATE_LIMIT_BACKEND       str    – "memory" | "redis"
        RATE_LIMIT_REDIS_URL     str    – required when backend is "redis"
        RATE_LIMIT_DEFAULT       str    – "requests/window_seconds" e.g. "100/60"
        RATE_LIMIT_RULES         dict   – {blueprint_or_endpoint: "requests/window"}
    """
    global _backend

    if not app.config.get("RATE_LIMIT_ENABLED", True):
        app.logger.info("Rate limiting is DISABLED via config.")
        return

    # ---- choose backend ------------------------------------------------
    backend_name = app.config.get("RATE_LIMIT_BACKEND", "memory")
    if backend_name == "redis":
        redis_url = app.config.get("RATE_LIMIT_REDIS_URL")
        if not redis_url:
            raise ValueError(
                "RATE_LIMIT_REDIS_URL must be set when RATE_LIMIT_BACKEND='redis'"
            )
        _backend = RedisBackend(redis_url)
        app.logger.info("Rate limiting: Redis backend (%s)", redis_url.split("@")[-1])
    else:
        _backend = MemoryBackend()
        app.logger.info("Rate limiting: in-memory backend")

    # ---- parse rules ---------------------------------------------------
    default_rule = _parse_rule(app.config.get("RATE_LIMIT_DEFAULT", "100/60"))
    rules: dict[str, Tuple[int, int]] = {}
    for pattern, rule_str in app.config.get("RATE_LIMIT_RULES", {}).items():
        rules[pattern] = _parse_rule(rule_str)

    # ---- before_request ------------------------------------------------
    @app.before_request
    def _rate_limit_check():
        # Only rate-limit API endpoints
        if not request.path.startswith("/api/"):
            return None

        endpoint = request.endpoint or ""
        max_req, window = _resolve_rule(endpoint, request.blueprint, rules, default_rule)

        client_ip = request.remote_addr or "unknown"
        key = f"rl:{endpoint}:{client_ip}"

        limited, remaining, reset_at = _backend.hit(key, max_req, window)

        # Stash info for the after_request header injection
        g._rate_limit_info = {
            "limit": max_req,
            "remaining": remaining,
            "reset": reset_at,
        }

        if limited:
            retry_after = max(1, reset_at - int(time.time()))
            response = jsonify({
                "error": "Too many requests",
                "message": "Rate limit exceeded. Try again later.",
            })
            response.status_code = 429
            response.headers["Retry-After"] = str(retry_after)
            _inject_headers(response, max_req, 0, reset_at)
            return response

        return None

    # ---- after_request -------------------------------------------------
    @app.after_request
    def _rate_limit_headers(response):
        info = getattr(g, "_rate_limit_info", None)
        if info:
            _inject_headers(response, info["limit"], info["remaining"], info["reset"])
        return response

    app.logger.info(
        "Rate limiting active — default %s req / %s s, %d custom rules",
        default_rule[0], default_rule[1], len(rules),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_rule(rule: str) -> Tuple[int, int]:
    """Parse ``'requests/window_seconds'`` into ``(max_requests, window_seconds)``."""
    parts = rule.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid rate-limit rule '{rule}'. Expected 'requests/seconds'.")
    return int(parts[0]), int(parts[1])


def _resolve_rule(
    endpoint: str,
    blueprint: Optional[str],
    rules: dict[str, Tuple[int, int]],
    default: Tuple[int, int],
) -> Tuple[int, int]:
    """
    Find the most specific rule that matches this request.

    Matching order (first match wins):
        1. Exact endpoint name   e.g. "auth.login"
        2. Blueprint name        e.g. "auth"
        3. Default rule
    """
    # exact endpoint match
    if endpoint in rules:
        return rules[endpoint]
    # blueprint match
    if blueprint and blueprint in rules:
        return rules[blueprint]
    return default


def _inject_headers(response, limit: int, remaining: int, reset: int) -> None:
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset)
