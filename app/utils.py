"""
Utility functions for the expenses dashboard.
"""

import os
from datetime import datetime


def allowed_file(filename: str, allowed_extensions: set = None) -> bool:
    """Check if file extension is allowed."""
    if allowed_extensions is None:
        allowed_extensions = {'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_file_size(filepath: str) -> str:
    """Get human-readable file size."""
    size = os.path.getsize(filepath)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def parse_date_string(date_str: str) -> tuple:
    """
    Parse date string like '1.03' or '01.03' to (month, day).
    Returns (month, day) as integers.
    """
    if not date_str:
        return None, None
    
    parts = date_str.split('.')
    if len(parts) != 2:
        return None, None
    
    try:
        month = int(parts[0])
        day = int(parts[1])
        return month, day
    except ValueError:
        return None, None


def format_date(month: int, day: int) -> str:
    """Format date as M.DD."""
    return f"{month}.{day:02d}"


def safe_float(value, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def generate_statement_filename(original_filename: str) -> str:
    """Generate a unique filename for uploaded statement."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = ''.join(c for c in original_filename if c.isalnum() or c in '._-')
    return f"{timestamp}_{safe_name}"
