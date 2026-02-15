"""
Decorators for authentication and authorization.
"""

from functools import wraps
from flask import request, jsonify, current_app

from app.services.auth_service import AuthService
from app.models.user import User


def token_required(f):
    """Decorator to require valid JWT token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Remove 'Bearer '
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        # Validate token
        success, user_data, message = AuthService.validate_token_middleware(
            token)
        if not success:
            return jsonify({'error': message}), 401

        # Add user data to request context
        request.current_user = user_data

        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """Decorator to require admin role. Includes token validation."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Remove 'Bearer '
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        # Validate token
        success, user_data, message = AuthService.validate_token_middleware(
            token)
        if not success:
            return jsonify({'error': message}), 401

        # Add user data to request context
        request.current_user = user_data

        # Check admin role
        if request.current_user.get('role') != 'admin':
            return jsonify({'error': 'Admin permissions required'}), 403

        return f(*args, **kwargs)

    return decorated


def supervisor_required(f):
    """Decorator to require supervisor role only (admin excluded). Includes token validation."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        success, user_data, message = AuthService.validate_token_middleware(token)
        if not success:
            return jsonify({'error': message}), 401

        request.current_user = user_data

        if request.current_user.get('role') != 'supervisor':
            return jsonify({'error': 'Supervisor permissions required'}), 403

        return f(*args, **kwargs)

    return decorated


def supervisor_or_admin_required(f):
    """Decorator to require supervisor or admin role. Includes token validation."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Remove 'Bearer '
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        # Validate token
        success, user_data, message = AuthService.validate_token_middleware(
            token)
        if not success:
            return jsonify({'error': message}), 401

        # Add user data to request context
        request.current_user = user_data

        # Check supervisor or admin role
        user_role = request.current_user.get('role')
        if user_role not in ['admin', 'supervisor']:
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


def resource_owner_or_admin(resource_id_param='id', owner_field='worker_id'):
    """
    Decorator to allow access to resource owner or admin/supervisor.

    Args:
        resource_id_param: Parameter name containing resource ID
        owner_field: Field in resource that contains owner ID
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

            # For workers, check resource ownership
            resource_id = kwargs.get(resource_id_param)
            if resource_id:
                # This would need to be customized based on the resource type
                # For now, we'll allow the route to handle ownership validation
                pass

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


def rate_limit(max_requests=100, window_minutes=60):
    """
    Basic rate limiting decorator.

    Args:
        max_requests: Maximum number of requests allowed
        window_minutes: Time window in minutes
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # This is a placeholder for rate limiting implementation
            # In production, you'd use Redis or similar for tracking
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
        except Exception:
            pass  # Don't fail request if logging fails

        return f(*args, **kwargs)

    return decorated
