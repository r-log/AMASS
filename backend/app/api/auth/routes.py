"""
Authentication API routes.
"""

from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService
from app.utils.decorators import token_required, admin_required, validate_json_request

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
@validate_json_request
def login():
    """User login endpoint."""
    try:
        print(f"\n{'#'*60}")
        print(f"[LOGIN ROUTE] Received login request")

        data = request.get_json()
        print(f"[LOGIN ROUTE] Request data keys: {list(data.keys())}")

        username = data.get('username')
        password = data.get('password')
        print(
            f"[LOGIN ROUTE] Username: '{username}', Password provided: {bool(password)}")

        if not username or not password:
            print(f"[LOGIN ROUTE] ❌ Missing credentials")
            return jsonify({'error': 'Username and password are required'}), 400

        print(f"[LOGIN ROUTE] Calling AuthService.authenticate_user...")
        success, user, message = AuthService.authenticate_user(
            username, password)
        print(
            f"[LOGIN ROUTE] Authentication result: success={success}, message='{message}'")

        if success:
            print(f"[LOGIN ROUTE] ✓ Authentication successful, generating token...")
            token = AuthService.generate_token(user)
            print(f"[LOGIN ROUTE] ✓ Token generated")

            session_data = AuthService.create_session_data(user)
            print(f"[LOGIN ROUTE] ✓ Session data created")

            response_data = {
                'success': True,
                'message': 'Login successful',
                'token': token,
                'user': session_data
            }
            print(
                f"[LOGIN ROUTE] ✓ Sending 200 response with data: {list(response_data.keys())}")
            print(f"{'#'*60}\n")

            return jsonify(response_data), 200
        else:
            print(f"[LOGIN ROUTE] ❌ Authentication failed: {message}")
            print(f"[LOGIN ROUTE] Sending 401 response")
            print(f"{'#'*60}\n")
            return jsonify({'error': message}), 401

    except Exception as e:
        print(f"[LOGIN ROUTE] ❌ Exception occurred: {str(e)}")
        print(f"[LOGIN ROUTE] Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'#'*60}\n")
        return jsonify({'error': f'Login failed: {str(e)}'}), 500


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """User logout endpoint."""
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace(
            'Bearer ', '') if auth_header.startswith('Bearer ') else ''

        success, message = AuthService.logout_user(token)

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Logout failed: {str(e)}'}), 500


@auth_bp.route('/verify', methods=['GET'])
@token_required
def verify_token():
    """Verify token validity."""
    try:
        return jsonify({
            'success': True,
            'message': 'Token is valid',
            'user': request.current_user
        }), 200

    except Exception as e:
        return jsonify({'error': f'Token verification failed: {str(e)}'}), 500


@auth_bp.route('/refresh', methods=['POST'])
@token_required
def refresh_token():
    """Refresh authentication token."""
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace(
            'Bearer ', '') if auth_header.startswith('Bearer ') else ''

        success, new_token, message = AuthService.refresh_token(token)

        if success:
            return jsonify({
                'message': message,
                'token': new_token
            }), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Token refresh failed: {str(e)}'}), 500


@auth_bp.route('/register', methods=['POST'])
@admin_required
@validate_json_request
def register():
    """Register new user (admin only)."""
    try:
        data = request.get_json()

        required_fields = ['username', 'password', 'full_name']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        success, user, message = AuthService.register_user(
            username=data['username'],
            password=data['password'],
            full_name=data['full_name'],
            role=data.get('role', 'worker'),
            created_by=request.current_user.get('user_id')
        )

        if success:
            return jsonify({
                'message': message,
                'user': user.to_dict() if user else None
            }), 201
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500


@auth_bp.route('/change-password', methods=['POST'])
@token_required
@validate_json_request
def change_password():
    """Change user password."""
    try:
        data = request.get_json()

        old_password = data.get('old_password')
        new_password = data.get('new_password')

        if not old_password or not new_password:
            return jsonify({'error': 'Old and new passwords are required'}), 400

        success, message = AuthService.change_password(
            user_id=request.current_user.get('user_id'),
            old_password=old_password,
            new_password=new_password
        )

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Password change failed: {str(e)}'}), 500


@auth_bp.route('/reset-password', methods=['POST'])
@admin_required
@validate_json_request
def reset_password():
    """Reset user password (admin only)."""
    try:
        data = request.get_json()

        user_id = data.get('user_id')
        new_password = data.get('new_password')

        if not user_id or not new_password:
            return jsonify({'error': 'User ID and new password are required'}), 400

        success, message = AuthService.reset_password(
            user_id=user_id,
            new_password=new_password,
            reset_by=request.current_user.get('user_id')
        )

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Password reset failed: {str(e)}'}), 500


@auth_bp.route('/users', methods=['GET'])
@token_required
def list_users():
    """List users, optionally filtered by role. Admin: any role. Supervisor: workers only."""
    try:
        from app.models.user import User

        user_role = request.current_user.get('role')
        role = request.args.get('role')

        if user_role == 'admin':
            if role:
                users = User.find_by_role(role)
            else:
                users = User.find_all_active()
        elif user_role == 'supervisor':
            if role == 'worker':
                users = User.find_by_role('worker')
            else:
                users = []
        else:
            return jsonify({'error': 'Insufficient permissions'}), 403

        return jsonify([u.to_dict() for u in users]), 200

    except Exception as e:
        return jsonify({'error': f'Failed to list users: {str(e)}'}), 500


@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    """Get current user profile."""
    try:
        from app.models.user import User

        user = User.find_by_id(request.current_user.get('user_id'))
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user': user.to_dict(),
            'permissions': AuthService.get_user_permissions(user)
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to get profile: {str(e)}'}), 500


@auth_bp.route('/profile', methods=['PUT'])
@token_required
@validate_json_request
def update_profile():
    """Update user profile."""
    try:
        data = request.get_json()
        user_id = request.current_user.get('user_id')

        # Only allow updating own profile unless admin
        target_user_id = data.get('user_id', user_id)
        if target_user_id != user_id:
            user_role = request.current_user.get('role')
            if user_role != 'admin':
                return jsonify({'error': 'Can only update own profile'}), 403

        success, message = AuthService.update_user_profile(
            user_id=target_user_id,
            full_name=data.get('full_name'),
            role=data.get('role'),
            is_active=data.get('is_active'),
            updated_by=user_id
        )

        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400

    except Exception as e:
        return jsonify({'error': f'Profile update failed: {str(e)}'}), 500
