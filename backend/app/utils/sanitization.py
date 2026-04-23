"""
Input sanitization and validation utilities for security.
Prevents XSS, SQL injection, and other input-based attacks.
"""

import re
from typing import Optional


def sanitize_string(value: str, max_length: int = 255) -> str:
    """
    Remove HTML/script tags and limit length.
    
    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not value:
        return ""
    
    # Remove HTML tags
    value = re.sub(r'<[^>]+>', '', value)
    
    # Remove script content
    value = re.sub(
        r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', 
        '', 
        value, 
        flags=re.IGNORECASE
    )
    
    # Trim whitespace and limit length
    return value.strip()[:max_length]


def sanitize_alphanumeric(
    value: str, 
    max_length: int = 255, 
    allow_underscore: bool = False, 
    allow_hyphen: bool = False
) -> str:
    """
    Keep only alphanumeric characters (and optionally _ or -).
    
    Args:
        value: Input string
        max_length: Maximum length
        allow_underscore: Allow underscore character
        allow_hyphen: Allow hyphen character
        
    Returns:
        Sanitized alphanumeric string
    """
    if not value:
        return ""
    
    # Build regex pattern
    pattern = r'[^a-zA-Z0-9'
    if allow_underscore:
        pattern += '_'
    if allow_hyphen:
        pattern += '-'
    pattern += ']'
    
    # Remove non-allowed characters
    cleaned = re.sub(pattern, '', value)
    
    return cleaned[:max_length]


def sanitize_join_code(value: str) -> str:
    """
    Ensure join code is exactly 6 uppercase alphanumeric characters.
    
    Args:
        value: Input join code
        
    Returns:
        Sanitized 6-character uppercase join code
        
    Raises:
        ValueError: If code is not exactly 6 characters after cleaning
    """
    cleaned = sanitize_alphanumeric(value, max_length=6).upper()
    
    if len(cleaned) != 6:
        raise ValueError("Join code must be exactly 6 alphanumeric characters")
    
    return cleaned


def validate_input(value: str, field_name: str, max_length: int = 255) -> str:
    """
    Comprehensive validation and sanitization for text inputs.
    Checks for XSS attempts and dangerous patterns.
    
    Args:
        value: Input string to validate
        field_name: Name of the field (for error messages)
        max_length: Maximum allowed length
        
    Returns:
        Sanitized and validated string
        
    Raises:
        ValueError: If input is invalid or contains dangerous content
    """
    if not value or not value.strip():
        raise ValueError(f"{field_name} cannot be empty or whitespace")
    
    # Sanitize first
    cleaned = sanitize_string(value, max_length)
    
    # Check for dangerous patterns (XSS attempts)
    dangerous_patterns = [
        r'javascript:',
        r'on\w+\s*=',  # onclick=, onerror=, onload=, etc.
        r'<iframe',
        r'<embed',
        r'<object',
        r'<script',
        r'eval\s*\(',
        r'expression\s*\(',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, cleaned, re.IGNORECASE):
            raise ValueError(
                f"Invalid {field_name}: contains potentially dangerous content"
            )
    
    return cleaned


def validate_email(email: str) -> str:
    """
    Validate and sanitize email address.
    
    Args:
        email: Email address to validate
        
    Returns:
        Lowercase, trimmed email
        
    Raises:
        ValueError: If email format is invalid
    """
    if not email:
        raise ValueError("Email cannot be empty")
    
    email = email.strip().lower()
    
    # Basic email regex (not perfect but catches most issues)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        raise ValueError("Invalid email format")
    
    if len(email) > 255:
        raise ValueError("Email too long")
    
    return email


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Check password strength (for user registration).
    
    Args:
        password: Password to check
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if len(password) > 100:
        return False, "Password too long (max 100 characters)"
    
    # Check for at least one letter and one number
    has_letter = bool(re.search(r'[a-zA-Z]', password))
    has_number = bool(re.search(r'\d', password))
    
    if not (has_letter and has_number):
        return False, "Password must contain both letters and numbers"
    
    return True, ""
