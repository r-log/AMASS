"""
Decorators for authentication and authorization.
"""

import threading
import time
from collections import defaultdict
from functools import wraps
from typing import Optional, Tuple, Any

from flask import request, jsonify, current_app

from app.services.auth_service import AuthService
from app.models.user import User


def _extract_and_validate_token() -> Tuple[Optional[Any], Optional[Any]]:
    """
    Extract JWT from Authorization header and validate.
    Returns (user_data, error_response) - if user_data is set, error_response is None.
    """
    token = None
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        try:
            token = auth_header.split(' ')[1]
        except IndexError:
            return None, (jsonify({'error': 'Invalid token format'}), 401)

    if not token:
        return None, (jsonify({'error': 'Token is missing'}), 401)

    success, user_data, message = AuthService.validate_token_middleware(token)
    if not success:
        return None, (jsonify({'error': message}), 401)

    return user_data, None


def token_required(f):
    """Decorator to require valid JWT token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_data, err = _extract_and_validate_token()
        if err:
            return err
        request.current_user = user_data
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator to require admin role. Includes token validation."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_data, err = _extract_and_validate_token()
        if err:
            return err
        request.current_user = user_data
        if request.current_user.get('role') != 'admin':
            return jsonify({'error': 'Admin permissions required'}), 403
        return f(*args, **kwargs)
    return decorated


def supervisor_required(f):
    """Decorator to require supervisor role only (admin excluded). Includes token validation."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_data, err = _extract_and_validate_token()
        if err:
            return err
        request.current_user = user_data
        if request.current_user.get('role') != 'supervisor':
            return jsonify({'error': 'Supervisor permissions required'}), 403
        return f(*args, **kwargs)
    return decorated


def supervisor_or_admin_required(f):
    """Decorator to require supervisor or admin role. Includes token validation."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_data, err = _extract_and_validate_token()
        if err:
            return err
        request.current_user = user_data
        if request.current_user.get('role') not in ['admin', 'supervisor']:
            return jsonify({'error': 'Supervisor or admin permissions required'}), 403
        return f(*args, **kwargs)
    return decorated


def role_required(*allowed_roles):
    """Decorator to require specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(request, 'current_user') or not request.current_user:
                return jsonify({'error': 'Authentication required'}), 401

            user_role = request.current_user.get('role')
            if user_role not in allowed_roles:
                return jsonify({
                    'error': f'Required role: {" or ".join(allowed_roles)}'
                }), 403

            return f(*args, **kwargs)

        return decorated
    return decorator


def resource_owner_or_admin(resource_id_param='id', model_class=None, owner_field='worker_id'):
    """
    Decorator to allow access to resource owner or admin/supervisor.

    Args:
        resource_id_param: URL parameter name containing resource ID
        model_class: Model class with find_by_id() to look up the resource
        owner_field: Attribute on the model that holds the owner's user ID
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(request, 'current_user') or not request.current_user:
                return jsonify({'error': 'Authentication required'}), 401

            user_id = request.current_user.get('user_id')
            user_role = request.current_user.get('role')

            # Admins and supervisors have full access
            if user_role in ['admin', 'supervisor']:
                return f(*args, **kwargs)

            # For workers, validate resource ownership
            resource_id = kwargs.get(resource_id_param)
            if resource_id and model_class is not None:
                resource = model_class.find_by_id(resource_id)
                if not resource:
                    return jsonify({'error': 'Resource not found'}), 404
                resource_owner_id = getattr(resource, owner_field, None)
                if resource_owner_id != user_id:
                    return jsonify({'error': 'Access denied — you do not own this resource'}), 403

            return f(*args, **kwargs)

        return decorated
    return decorator


def validate_json_request(f):
    """Decorator to validate that request contains valid JSON."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.is_json:
            return jsonify({'error': 'Request must contain valid JSON'}), 400

        try:
            request.get_json()
        except Exception:
            return jsonify({'error': 'Invalid JSON format'}), 400

        return f(*args, **kwargs)

    return decorated


class _RateLimitStore:
    """Thread-safe in-memory sliding-window rate limiter."""

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_limited(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            # Prune old entries
            timestamps = self._requests[key]
            self._requests[key] = [t for t in timestamps if t > cutoff]
            if len(self._requests[key]) >= max_requests:
                return True
            self._requests[key].append(now)
            return False


_rate_limit_store = _RateLimitStore()


def rate_limit(max_requests=100, window_minutes=60):
    """
    In-memory sliding-window rate limiter keyed by client IP.

    For multi-process / distributed deployments, replace the store
    with Redis or similar.

    Args:
        max_requests: Maximum number of requests allowed in the window
        window_minutes: Time window in minutes
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            client_ip = request.remote_addr or 'unknown'
            key = f"{f.__name__}:{client_ip}"
            if _rate_limit_store.is_limited(key, max_requests, window_minutes * 60):
                return jsonify({
                    'error': 'Too many requests',
                    'message': f'Rate limit exceeded. Try again later.'
                }), 429
            return f(*args, **kwargs)

        return decorated
    return decorator


def log_endpoint_access(f):
    """Decorator to log endpoint access for audit trails."""
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            user_id = getattr(request, 'current_user', {}
                              ).get('user_id', 'anonymous')
            endpoint = f"{request.method} {request.endpoint}"
            current_app.logger.info(
                f"Endpoint access: {endpoint} by user {user_id}")
        except Exception as e:
            current_app.logger.debug("Audit logging failed: %s", e)

        return f(*args, **kwargs)

    return decorated
