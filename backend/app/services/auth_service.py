"""
Authentication and authorization service.
Handles user authentication, token management, and access control.
"""

import jwt as pyjwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app

from app.models.user import User
from app.models.notification import Notification


class AuthService:
    """Service for handling authentication and authorization."""

    @staticmethod
    def authenticate_user(username: str, password: str) -> Tuple[bool, Optional[User], str]:
        """
        Authenticate a user with username and password.

        Returns:
            Tuple of (success, user_object, message)
        """
        try:
            print(f"\n{'='*60}")
            print(f"[AUTH DEBUG] Login attempt for username: '{username}'")

            # Find user by username
            user = User.find_by_username(username)
            print(f"[AUTH DEBUG] User found in database: {user is not None}")

            if not user:
                print(f"[AUTH DEBUG] ❌ User not found")
                return False, None, "Invalid username or password"

            print(
                f"[AUTH DEBUG] User ID: {user.id}, Full name: {user.full_name}, Role: {user.role}")
            print(f"[AUTH DEBUG] User is_active: {user.is_active}")

            if not user.is_active:
                print(f"[AUTH DEBUG] ❌ Account is deactivated")
                return False, None, "Account is deactivated"

            # Verify password
            print(
                f"[AUTH DEBUG] Password hash from DB (first 30 chars): {user.password_hash[:30]}...")
            print(
                f"[AUTH DEBUG] Password hash method: {user.password_hash.split('$')[0] if '$' in user.password_hash else 'unknown'}")

            password_valid = check_password_hash(user.password_hash, password)
            print(
                f"[AUTH DEBUG] Password verification result: {password_valid}")

            if not password_valid:
                print(f"[AUTH DEBUG] ❌ Password verification failed")
                return False, None, "Invalid username or password"

            print(f"[AUTH DEBUG] ✓ Password verified successfully")

            # Update last login
            user.update_last_login()
            print(f"[AUTH DEBUG] ✓ Last login updated")

            print(f"[AUTH DEBUG] ✓ Authentication successful!")
            print(f"{'='*60}\n")
            return True, user, "Authentication successful"

        except Exception as e:
            print(f"[AUTH DEBUG] ❌ Exception during authentication: {str(e)}")
            print(f"[AUTH DEBUG] Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            return False, None, f"Authentication error: {str(e)}"

    @staticmethod
    def generate_token(user: User) -> str:
        """Generate JWT token for authenticated user."""
        try:
            print(
                f"[TOKEN DEBUG] Generating JWT token for user: {user.username} (ID: {user.id})")

            payload = {
                'user_id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'role': user.role,
                'exp': datetime.utcnow() + timedelta(hours=current_app.config.get('JWT_EXPIRATION_HOURS', 24)),
                'iat': datetime.utcnow()
            }
            print(f"[TOKEN DEBUG] Payload created: {payload}")

            token = pyjwt.encode(
                payload,
                current_app.config['SECRET_KEY'],
                algorithm='HS256'
            )
            print(f"[TOKEN DEBUG] Token encoded, type: {type(token)}")

            # PyJWT 2.x returns string directly, no need to decode
            final_token = token if isinstance(
                token, str) else token.decode('utf-8')
            print(
                f"[TOKEN DEBUG] ✓ Token generated successfully (length: {len(final_token)})")
            print(f"[TOKEN DEBUG] Token preview: {final_token[:50]}...")
            return final_token

        except Exception as e:
            print(f"[TOKEN DEBUG] ❌ Token generation failed: {str(e)}")
            print(f"[TOKEN DEBUG] Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"Token generation failed: {str(e)}")

    @staticmethod
    def verify_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Verify and decode JWT token.

        Returns:
            Tuple of (success, payload, message)
        """
        try:
            payload = pyjwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )

            # Verify user still exists and is active
            user = User.find_by_id(payload.get('user_id'))
            if not user or not user.is_active:
                return False, None, "User account not found or deactivated"

            return True, payload, "Token is valid"

        except pyjwt.ExpiredSignatureError:
            return False, None, "Token has expired"
        except pyjwt.InvalidTokenError:
            return False, None, "Invalid token"
        except Exception as e:
            return False, None, f"Token verification error: {str(e)}"

    @staticmethod
    def refresh_token(token: str) -> Tuple[bool, Optional[str], str]:
        """
        Refresh an existing token if it's still valid.

        Returns:
            Tuple of (success, new_token, message)
        """
        success, payload, message = AuthService.verify_token(token)

        if not success:
            return False, None, message

        try:
            user = User.find_by_id(payload.get('user_id'))
            if not user:
                return False, None, "User not found"

            new_token = AuthService.generate_token(user)
            return True, new_token, "Token refreshed successfully"

        except Exception as e:
            return False, None, f"Token refresh failed: {str(e)}"

    @staticmethod
    def register_user(username: str, password: str, full_name: str,
                      role: str = 'worker', created_by: Optional[int] = None) -> Tuple[bool, Optional[User], str]:
        """
        Register a new user.

        Returns:
            Tuple of (success, user_object, message)
        """
        try:
            # Check if username already exists
            existing_user = User.find_by_username(username)
            if existing_user:
                return False, None, "Username already exists"

            # Validate role
            valid_roles = ['worker', 'supervisor', 'admin']
            if role not in valid_roles:
                return False, None, f"Invalid role. Must be one of: {', '.join(valid_roles)}"

            # Create user
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                full_name=full_name,
                role=role,
                is_active=True
            )

            user.save()

            # Create welcome notification
            if user.id:
                Notification.create_for_user(
                    user.id,
                    'system',
                    'Welcome!',
                    f'Welcome to the Electrician Log system, {full_name}!'
                )

            return True, user, "User registered successfully"

        except Exception as e:
            return False, None, f"Registration failed: {str(e)}"

    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Change user password.

        Returns:
            Tuple of (success, message)
        """
        try:
            user = User.find_by_id(user_id)
            if not user:
                return False, "User not found"

            # Verify old password
            if not check_password_hash(user.password_hash, old_password):
                return False, "Current password is incorrect"

            # Validate new password
            if len(new_password) < 6:
                return False, "New password must be at least 6 characters long"

            # Update password
            user.password_hash = generate_password_hash(new_password)
            user.save()

            return True, "Password changed successfully"

        except Exception as e:
            return False, f"Password change failed: {str(e)}"

    @staticmethod
    def reset_password(user_id: int, new_password: str, reset_by: int) -> Tuple[bool, str]:
        """
        Reset user password (admin/supervisor function).

        Returns:
            Tuple of (success, message)
        """
        try:
            user = User.find_by_id(user_id)
            if not user:
                return False, "User not found"

            reset_user = User.find_by_id(reset_by)
            if not reset_user or not reset_user.can_manage_users():
                return False, "Insufficient permissions"

            # Validate new password
            if len(new_password) < 6:
                return False, "New password must be at least 6 characters long"

            # Update password
            user.password_hash = generate_password_hash(new_password)
            user.save()

            # Notify user of password reset
            Notification.create_for_user(
                user_id,
                'system',
                'Password Reset',
                f'Your password has been reset by {reset_user.full_name}. Please change it after your next login.'
            )

            return True, "Password reset successfully"

        except Exception as e:
            return False, f"Password reset failed: {str(e)}"

    @staticmethod
    def update_user_profile(user_id: int, full_name: Optional[str] = None,
                            role: Optional[str] = None, is_active: Optional[bool] = None,
                            updated_by: Optional[int] = None) -> Tuple[bool, str]:
        """
        Update user profile information.

        Returns:
            Tuple of (success, message)
        """
        try:
            user = User.find_by_id(user_id)
            if not user:
                return False, "User not found"

            # Check permissions for role/status changes
            if (role is not None or is_active is not None) and updated_by:
                updater = User.find_by_id(updated_by)
                if not updater or not updater.can_manage_users():
                    return False, "Insufficient permissions to change user role or status"

            # Update fields
            if full_name is not None:
                user.full_name = full_name

            if role is not None:
                valid_roles = ['worker', 'supervisor', 'admin']
                if role not in valid_roles:
                    return False, f"Invalid role. Must be one of: {', '.join(valid_roles)}"
                user.role = role

            if is_active is not None:
                if is_active:
                    user.activate()
                else:
                    user.deactivate()

            user.save()

            return True, "User profile updated successfully"

        except Exception as e:
            return False, f"Profile update failed: {str(e)}"

    @staticmethod
    def get_user_permissions(user: User) -> Dict[str, bool]:
        """Get user permissions based on role."""
        return {
            'can_manage_users': user.can_manage_users(),
            'can_delete_any_log': user.can_delete_any_log(),
            'can_edit_any_log': user.can_edit_any_log(),
            'can_manage_critical_sectors': user.can_manage_critical_sectors(),
            'is_admin': user.is_admin(),
            'is_supervisor': user.is_supervisor(),
            'is_worker': user.is_worker()
        }

    @staticmethod
    def check_permission(user: User, required_roles: list,
                         resource_owner_id: Optional[int] = None) -> bool:
        """
        Check if user has required permissions.

        Args:
            user: User object
            required_roles: List of roles that can access the resource
            resource_owner_id: ID of resource owner (for own-resource access)

        Returns:
            True if user has permission, False otherwise
        """
        # Check if user has required role
        if user.role in required_roles:
            return True

        # Check if user owns the resource (for worker role)
        if resource_owner_id and user.id == resource_owner_id:
            return True

        return False

    @staticmethod
    def validate_token_middleware(token: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Middleware function to validate token and return user info.

        Returns:
            Tuple of (success, user_data, message)
        """
        if not token:
            return False, None, "No token provided"

        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]

        success, payload, message = AuthService.verify_token(token)

        if success:
            # Add permissions to payload
            user = User.find_by_id(payload.get('user_id'))
            if user:
                payload['permissions'] = AuthService.get_user_permissions(user)

            return True, payload, "Token validated successfully"

        return False, None, message

    @staticmethod
    def create_session_data(user: User) -> Dict[str, Any]:
        """Create session data for authenticated user."""
        return {
            'user_id': user.id,
            'username': user.username,
            'full_name': user.full_name,
            'role': user.role,
            'permissions': AuthService.get_user_permissions(user),
            'last_login': user.last_login.isoformat() if user.last_login else None
        }

    @staticmethod
    def logout_user(token: str) -> Tuple[bool, str]:
        """
        Logout user (currently just validates token exists).
        In a production system, you might maintain a token blacklist.

        Returns:
            Tuple of (success, message)
        """
        success, payload, message = AuthService.verify_token(token)

        if success:
            return True, "Logged out successfully"
        else:
            return False, message
