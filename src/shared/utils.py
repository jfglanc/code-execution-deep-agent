"""Shared utilities for deep research system.

This module provides common utilities used across all research components,
including date formatting.
"""

from datetime import datetime


def get_today_str() -> str:
    """Get current date in a human-readable format.
    
    Returns:
        Formatted date string (e.g., "Mon Aug 12, 2025")
    """
    return datetime.now().strftime("%a %b %-d, %Y")


