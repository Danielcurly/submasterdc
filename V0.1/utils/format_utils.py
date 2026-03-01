#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Format Utility Functions
Provides various data formatting features
"""

from core.models import ISO_LANG_MAP


def format_file_size(size_bytes: int) -> str:
    """
    Format file size
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted string (e.g. "1.5 GB")
    """
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_timestamp(seconds: float) -> str:
    """
    Format timestamp to SRT format
    
    Args:
        seconds: Seconds
    
    Returns:
        SRT format timestamp (00:00:00,000)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def get_lang_name(code: str) -> str:
    """
    Get English name for language code
    
    Args:
        code: Language code (e.g. 'zh', 'en')
    
    Returns:
        Language name
    """
    return ISO_LANG_MAP.get(code.lower(), code)


def format_duration(seconds: int) -> str:
    """
    Format duration
    
    Args:
        seconds: Seconds
    
    Returns:
        Formatted duration (e.g. "1h 23m")
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate text
    
    Args:
        text: Original text
        max_length: Maximum length
        suffix: Suffix
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_percentage(current: int, total: int, decimals: int = 1) -> str:
    """
    Format percentage
    
    Args:
        current: Current value
        total: Total value
        decimals: Decimal places
    
    Returns:
        Percentage string (e.g. "75.5%")
    """
    if total == 0:
        return "0%"
    
    percentage = (current / total) * 100
    return f"{percentage:.{decimals}f}%"