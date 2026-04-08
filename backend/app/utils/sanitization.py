"""
Input sanitization utilities to prevent SQL injection, XSS, and other attacks.
"""
import html
import re
from typing import Optional

def sanitize_string(value: str, max_length: int = 255, allow_special: bool = False) -> str:
    """
    Comprehensive input sanitization:
    - Strip whitespace
    - Limit length
    - HTML escape special characters
    - Remove control characters
    """
    if not value or not isinstance(value, str):
        return ""
    
    # Strip leading/trailing whitespace
    value = value.strip()
    
    # Remove control characters (except newlines in some contexts)
    value = ''.join(char for char in value if not (ord(char) < 32 and char not in '\n\t'))
    
    # Limit length
    value = value[:max_length]
    
    # HTML escape to prevent XSS
    value = html.escape(value, quote=True)
    
    return value


def sanitize_alphanumeric(value: str, max_length: int = 255, allow_underscore: bool = True, allow_hyphen: bool = True) -> str:
    """
    Strict alphanumeric sanitization for IDs and codes.
    Allows only: a-z A-Z 0-9 optionally: _ -
    """
    if not value or not isinstance(value, str):
        return ""
    
    value = value.strip()
    
    # Build allowed character pattern
    pattern = r'^[a-zA-Z0-9'
    if allow_underscore:
        pattern += '_'
    if allow_hyphen:
        pattern += '-'
    pattern += r']+$'
    
    if not re.match(pattern, value):
        raise ValueError(f"Invalid characters in input. Only alphanumeric{', underscore' if allow_underscore else ''}{', hyphen' if allow_hyphen else ''} allowed.")
    
    return value[:max_length]


def sanitize_join_code(value: str) -> str:
    """
    Sanitize join codes - alphanumeric only, uppercase.
    """
    if not value or not isinstance(value, str):
        return ""
    
    value = value.strip().upper()
    
    # Join codes should be simple alphanumeric
    if not re.match(r'^[A-Z0-9]+$', value):
        raise ValueError("Join code must be alphanumeric only")
    
    if len(value) > 10:
        raise ValueError("Join code must be 10 characters or less")
    
    return value


def prevent_sql_injection(value: str) -> bool:
    """
    Basic SQL injection pattern detection.
    Returns True if suspicious patterns detected.
    """
    if not value or not isinstance(value, str):
        return False
    
    # Common SQL injection patterns
    suspicious_patterns = [
        r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(-{2}|/\*|\*/|xp_|sp_)",  # SQL comments and stored procedures
        r"(;|\||&&)",  # Command separators
        r"(<script|javascript:|onerror=|onload=)",  # XSS patterns
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            return True
    
    return False


def validate_input(value: str, field_name: str = "input", max_length: int = 255) -> str:
    """
    Combined validation and sanitization with security checks.
    """
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    
    # Check for injection attempts
    if prevent_sql_injection(value):
        raise ValueError(f"{field_name} contains invalid characters or patterns")
    
    # Sanitize
    sanitized = sanitize_string(value, max_length=max_length)
    
    # Ensure not empty after sanitization
    if not sanitized or len(sanitized.strip()) == 0:
        raise ValueError(f"{field_name} cannot be empty")
    
    return sanitized
