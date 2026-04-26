"""
Decorators for authentication and authorization.
"""

from functools import wraps
from typing import Optional, Tuple, Any

from flask import request, jsonify, current_app

from app.services.auth_service import AuthService


def extract_bearer_token(auth_header: str) -> Optional[str]:
    """Extract the token from a ``Bearer <token>`` Authorization header.

    Returns the token string, or ``None`` if the header is missing,
    empty, or doesn't start with "Bearer ".  Centralizes the parsing
    that was previously duplicated across decorators and route handlers
    with inconsistent approaches (split vs replace).
    """
    if not auth_header:
        return None
    parts = auth_header.split(' ', 1)
    if len(parts) != 2 or parts[0] != 'Bearer':
        return None
    token = parts[1].strip()
    return token if token else None


def _extract_and_validate_token() -> Tuple[Optional[Any], Optional[Any]]:
    """
    Extract JWT from Authorization header and validate.
    Returns (user_data, error_response) - if user_data is set, error_response is None.
    """
    token = None
    if 'Authorization' in request.headers:
        token = extract_bearer_token(request.headers['Authorization'])
        if token is None and request.headers['Authorization']:
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
