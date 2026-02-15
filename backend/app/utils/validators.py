"""
Input validation utilities.
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime, date


def validate_coordinates(x: float, y: float) -> Tuple[bool, str]:
    """
    Validate that coordinates are within the 0-1 range.

    Args:
        x: X coordinate
        y: Y coordinate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        x = float(x)
        y = float(y)

        if x < 0 or x > 1:
            return False, "X coordinate must be between 0 and 1"
        if y < 0 or y > 1:
            return False, "Y coordinate must be between 0 and 1"

        return True, ""
    except (ValueError, TypeError):
        return False, "Coordinates must be valid numbers"


def validate_work_log_data(data: Dict[str, Any]) -> List[str]:
    """
    Validate work log data comprehensively.

    Args:
        data: Work log data dictionary

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Required fields
    required_fields = ['floor_id', 'x_coord',
                       'y_coord', 'work_date', 'work_type']
    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: {field}")

    # Validate coordinates
    if 'x_coord' in data and 'y_coord' in data:
        is_valid, error = validate_coordinates(
            data['x_coord'], data['y_coord'])
        if not is_valid:
            errors.append(error)

    # Validate floor_id
    if 'floor_id' in data:
        try:
            floor_id = int(data['floor_id'])
            if floor_id < 1:
                errors.append("Floor ID must be positive")
        except (ValueError, TypeError):
            errors.append("Floor ID must be a valid integer")

    # Validate work_date
    if 'work_date' in data:
        if not validate_date_format(data['work_date']):
            errors.append("Work date must be in YYYY-MM-DD format")

    # Validate work_type
    if 'work_type' in data:
        valid_work_types = ['cable_laying', 'installation',
                            'maintenance', 'inspection', 'other']
        if data['work_type'] not in valid_work_types:
            errors.append(
                f"Invalid work type. Must be one of: {', '.join(valid_work_types)}")

    # Validate cable_meters if provided
    if 'cable_meters' in data and data['cable_meters'] is not None:
        try:
            meters = float(data['cable_meters'])
            if meters < 0:
                errors.append("Cable meters must be non-negative")
        except (ValueError, TypeError):
            errors.append("Cable meters must be a valid number")

    # Validate hours_worked if provided
    if 'hours_worked' in data and data['hours_worked'] is not None:
        try:
            hours = float(data['hours_worked'])
            if hours < 0 or hours > 24:
                errors.append("Hours worked must be between 0 and 24")
        except (ValueError, TypeError):
            errors.append("Hours worked must be a valid number")

    # Validate priority if provided
    if 'priority' in data and data['priority'] is not None:
        valid_priorities = ['low', 'medium', 'high', 'critical']
        if data['priority'] not in valid_priorities:
            errors.append(
                f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")

    # Validate status if provided
    if 'status' in data and data['status'] is not None:
        valid_statuses = ['pending', 'in_progress', 'completed', 'on_hold']
        if data['status'] not in valid_statuses:
            errors.append(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}")

    return errors


def validate_cable_route(route_points: List[Dict[str, float]]) -> Tuple[bool, str]:
    """
    Validate cable route points.

    Args:
        route_points: List of dictionaries with x and y coordinates

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not route_points or not isinstance(route_points, list):
        return False, "Route points must be a non-empty list"

    if len(route_points) < 2:
        return False, "Route must have at least 2 points"

    for i, point in enumerate(route_points):
        if not isinstance(point, dict):
            return False, f"Route point {i} must be a dictionary"

        if 'x' not in point or 'y' not in point:
            return False, f"Route point {i} must have 'x' and 'y' coordinates"

        is_valid, error = validate_coordinates(point['x'], point['y'])
        if not is_valid:
            return False, f"Route point {i}: {error}"

    return True, ""


def validate_date_format(date_string: str) -> bool:
    """
    Validate date string format (YYYY-MM-DD).

    Args:
        date_string: Date string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except (ValueError, TypeError):
        return False


def validate_date_range(start_date: str, end_date: str) -> Tuple[bool, str]:
    """
    Validate date range.

    Args:
        start_date: Start date string (YYYY-MM-DD)
        end_date: End date string (YYYY-MM-DD)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not validate_date_format(start_date):
        return False, "Start date must be in YYYY-MM-DD format"

    if not validate_date_format(end_date):
        return False, "End date must be in YYYY-MM-DD format"

    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        if start > end:
            return False, "Start date must be before or equal to end date"

        return True, ""
    except Exception as e:
        return False, f"Date validation error: {str(e)}"


def validate_user_data(data: Dict[str, Any], is_update: bool = False) -> List[str]:
    """
    Validate user data for registration or update.

    Args:
        data: User data dictionary
        is_update: True if this is an update operation

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Required fields for new user
    if not is_update:
        required_fields = ['username', 'password', 'full_name']
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Missing required field: {field}")

    # Validate username
    if 'username' in data:
        username = data['username']
        if len(username) < 3:
            errors.append("Username must be at least 3 characters long")
        if len(username) > 50:
            errors.append("Username must not exceed 50 characters")
        if not username.replace('_', '').replace('-', '').isalnum():
            errors.append(
                "Username can only contain letters, numbers, hyphens, and underscores")

    # Validate password
    if 'password' in data and not is_update:
        password = data['password']
        if len(password) < 6:
            errors.append("Password must be at least 6 characters long")
        if len(password) > 100:
            errors.append("Password must not exceed 100 characters")

    # Validate full_name
    if 'full_name' in data:
        full_name = data['full_name']
        if len(full_name) < 2:
            errors.append("Full name must be at least 2 characters long")
        if len(full_name) > 100:
            errors.append("Full name must not exceed 100 characters")

    # Validate role
    if 'role' in data:
        valid_roles = ['worker', 'supervisor', 'admin']
        if data['role'] not in valid_roles:
            errors.append(
                f"Invalid role. Must be one of: {', '.join(valid_roles)}")

    return errors


def validate_email(email: str) -> bool:
    """
    Basic email validation.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    if not email or '@' not in email:
        return False

    parts = email.split('@')
    if len(parts) != 2:
        return False

    username, domain = parts
    if not username or not domain:
        return False

    if '.' not in domain:
        return False

    return True


def validate_positive_number(value: Any, field_name: str) -> Tuple[bool, str]:
    """
    Validate that a value is a positive number.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        num = float(value)
        if num <= 0:
            return False, f"{field_name} must be positive"
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name} must be a valid number"


def validate_integer_range(value: Any, min_val: int, max_val: int, field_name: str) -> Tuple[bool, str]:
    """
    Validate that a value is an integer within a specified range.

    Args:
        value: Value to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        field_name: Name of the field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        num = int(value)
        if num < min_val or num > max_val:
            return False, f"{field_name} must be between {min_val} and {max_val}"
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name} must be a valid integer"


def sanitize_string(text: str, max_length: int = None) -> str:
    """
    Sanitize string input by stripping whitespace and limiting length.

    Args:
        text: String to sanitize
        max_length: Maximum length (optional)

    Returns:
        Sanitized string
    """
    if not isinstance(text, str):
        return ""

    sanitized = text.strip()

    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def validate_floor_data(data: Dict[str, Any]) -> List[str]:
    """
    Validate floor data.

    Args:
        data: Floor data dictionary

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Required fields
    required_fields = ['name', 'floor_number']
    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append(f"Missing required field: {field}")

    # Validate floor_number
    if 'floor_number' in data:
        try:
            floor_num = int(data['floor_number'])
            if floor_num < -10 or floor_num > 100:
                errors.append("Floor number must be between -10 and 100")
        except (ValueError, TypeError):
            errors.append("Floor number must be a valid integer")

    # Validate name
    if 'name' in data:
        name = data['name']
        if not isinstance(name, str) or len(name.strip()) < 1:
            errors.append("Floor name cannot be empty")
        if len(name) > 100:
            errors.append("Floor name must not exceed 100 characters")

    return errors
