"""
Common helper functions and utilities.
"""

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import math
import os
import json


def calculate_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Calculate Euclidean distance between two points.

    Args:
        x1, y1: Coordinates of first point
        x2, y2: Coordinates of second point

    Returns:
        Distance as a float
    """
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def format_datetime(dt: Optional[datetime], format_string: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format datetime object to string.

    Args:
        dt: Datetime object to format
        format_string: Format string (default: 'YYYY-MM-DD HH:MM:SS')

    Returns:
        Formatted datetime string or empty string if dt is None
    """
    if dt is None:
        return ""

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt

    return dt.strftime(format_string)


def format_date(date_obj: Any, format_string: str = '%Y-%m-%d') -> str:
    """
    Format date object to string.

    Args:
        date_obj: Date object to format
        format_string: Format string (default: 'YYYY-MM-DD')

    Returns:
        Formatted date string
    """
    if date_obj is None:
        return ""

    if isinstance(date_obj, str):
        return date_obj

    if isinstance(date_obj, datetime):
        return date_obj.strftime(format_string)

    return str(date_obj)


def generate_export_filename(prefix: str, export_format: str = 'json', include_timestamp: bool = True) -> str:
    """
    Generate a filename for exports.

    Args:
        prefix: Filename prefix (e.g., 'work_logs')
        export_format: File format extension (e.g., 'json', 'csv')
        include_timestamp: Whether to include timestamp in filename

    Returns:
        Generated filename
    """
    if include_timestamp:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{prefix}_{timestamp}.{export_format}"
    else:
        return f"{prefix}.{export_format}"


def sanitize_input(text: str, remove_html: bool = True, max_length: Optional[int] = None) -> str:
    """
    Sanitize text input.

    Args:
        text: Text to sanitize
        remove_html: Remove HTML tags
        max_length: Maximum length to trim to

    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        return ""

    sanitized = text.strip()

    if remove_html:
        # Basic HTML tag removal
        import re
        sanitized = re.sub(r'<[^>]+>', '', sanitized)

    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized


def paginate_results(items: List[Any], page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    """
    Paginate a list of items.

    Args:
        items: List of items to paginate
        page: Page number (1-indexed)
        per_page: Items per page

    Returns:
        Dictionary with pagination info and items
    """
    total_items = len(items)
    total_pages = math.ceil(total_items / per_page) if total_items > 0 else 1

    # Ensure page is within valid range
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page

    return {
        'items': items[start_idx:end_idx],
        'page': page,
        'per_page': per_page,
        'total_items': total_items,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages
    }


def parse_date_or_datetime(date_string: str) -> Optional[datetime]:
    """
    Parse date or datetime string to datetime object.

    Args:
        date_string: Date string to parse

    Returns:
        Datetime object or None if parsing fails
    """
    if not date_string:
        return None

    # Try different formats
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%d-%m-%Y',
        '%d/%m/%Y'
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue

    return None


def get_date_range(days: int = 7, end_date: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """
    Get start and end dates for a date range.

    Args:
        days: Number of days to go back
        end_date: End date (defaults to now)

    Returns:
        Tuple of (start_date, end_date)
    """
    if end_date is None:
        end_date = datetime.now()

    start_date = end_date - timedelta(days=days)

    return start_date, end_date


def round_to_decimal_places(value: float, places: int = 2) -> float:
    """
    Round a float to specified decimal places.

    Args:
        value: Value to round
        places: Number of decimal places

    Returns:
        Rounded value
    """
    return round(value, places)


def calculate_percentage(part: float, whole: float, decimal_places: int = 1) -> float:
    """
    Calculate percentage.

    Args:
        part: Part value
        whole: Whole value
        decimal_places: Number of decimal places

    Returns:
        Percentage value
    """
    if whole == 0:
        return 0.0

    percentage = (part / whole) * 100
    return round(percentage, decimal_places)


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge multiple dictionaries.

    Args:
        *dicts: Variable number of dictionaries to merge

    Returns:
        Merged dictionary
    """
    result = {}
    for d in dicts:
        if d:
            result.update(d)
    return result


def safe_get(dictionary: Dict[str, Any], *keys, default=None) -> Any:
    """
    Safely get nested dictionary value.

    Args:
        dictionary: Dictionary to get value from
        *keys: Keys to traverse
        default: Default value if key not found

    Returns:
        Value or default
    """
    current = dictionary
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return current if current is not None else default


def chunks(lst: List[Any], n: int) -> List[List[Any]]:
    """
    Split a list into chunks of size n.

    Args:
        lst: List to split
        n: Chunk size

    Returns:
        List of chunks
    """
    return [lst[i:i + n] for i in range(0, len(lst), n)]


def is_within_bounds(x: float, y: float, bounds: Dict[str, float]) -> bool:
    """
    Check if a point is within specified bounds.

    Args:
        x, y: Point coordinates
        bounds: Dictionary with 'x', 'y', 'width', 'height'

    Returns:
        True if point is within bounds
    """
    return (bounds['x'] <= x <= bounds['x'] + bounds['width'] and
            bounds['y'] <= y <= bounds['y'] + bounds['height'])


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., '1.5 MB')
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Ensure a directory exists, create if it doesn't.

    Args:
        directory_path: Path to directory

    Returns:
        True if directory exists or was created
    """
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
        return True
    except Exception as e:
        print(f"Error creating directory {directory_path}: {e}")
        return False


def read_json_file(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Read and parse JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data or None if error
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading JSON file {file_path}: {e}")
        return None


def write_json_file(file_path: str, data: Dict[str, Any], indent: int = 2) -> bool:
    """
    Write data to JSON file.

    Args:
        file_path: Path to JSON file
        data: Data to write
        indent: JSON indentation

    Returns:
        True if successful
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing JSON file {file_path}: {e}")
        return False


def get_time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string.

    Args:
        dt: Datetime to compare

    Returns:
        Time ago string (e.g., '5 minutes ago')
    """
    if not dt:
        return "unknown"

    if isinstance(dt, str):
        dt = parse_date_or_datetime(dt)
        if not dt:
            return "unknown"

    now = datetime.now()
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    else:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"


def create_success_response(message: str, data: Any = None, status_code: int = 200) -> Tuple[Dict[str, Any], int]:
    """
    Create standardized success response.

    Args:
        message: Success message
        data: Response data
        status_code: HTTP status code

    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        'success': True,
        'message': message
    }
    if data is not None:
        response['data'] = data

    return response, status_code


def create_error_response(message: str, errors: Optional[List[str]] = None, status_code: int = 400) -> Tuple[Dict[str, Any], int]:
    """
    Create standardized error response.

    Args:
        message: Error message
        errors: List of detailed errors
        status_code: HTTP status code

    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        'success': False,
        'error': message
    }
    if errors:
        response['errors'] = errors

    return response, status_code


def generate_unique_id(prefix: str = "") -> str:
    """
    Generate a unique identifier.

    Args:
        prefix: Optional prefix for the ID

    Returns:
        Unique ID string
    """
    import uuid
    unique_id = str(uuid.uuid4())

    if prefix:
        return f"{prefix}_{unique_id}"
    return unique_id


def normalize_coordinates(x: float, y: float, width: float, height: float) -> Tuple[float, float]:
    """
    Normalize coordinates to 0-1 range.

    Args:
        x, y: Coordinates to normalize
        width, height: Dimensions to normalize against

    Returns:
        Tuple of normalized (x, y)
    """
    if width == 0 or height == 0:
        return 0.0, 0.0

    normalized_x = x / width
    normalized_y = y / height

    # Clamp to 0-1 range
    normalized_x = max(0.0, min(1.0, normalized_x))
    normalized_y = max(0.0, min(1.0, normalized_y))

    return normalized_x, normalized_y


def denormalize_coordinates(x: float, y: float, width: float, height: float) -> Tuple[float, float]:
    """
    Denormalize coordinates from 0-1 range to actual dimensions.

    Args:
        x, y: Normalized coordinates (0-1)
        width, height: Target dimensions

    Returns:
        Tuple of denormalized (x, y)
    """
    return x * width, y * height
