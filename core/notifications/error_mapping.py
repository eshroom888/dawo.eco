"""Error type mapping for publish notifications.

Story 4-7: Discord Publish Notifications (Task 8)

Maps internal error types to user-friendly messages for
Discord failure notifications.

Usage:
    from core.notifications.error_mapping import get_user_friendly_error

    message = get_user_friendly_error("RATE_LIMIT", raw_error)
"""

import logging

logger = logging.getLogger(__name__)

# Error types for user-friendly messages
ERROR_TYPE_MESSAGES = {
    "API_ERROR": "Instagram API returned an error",
    "RATE_LIMIT": "Instagram rate limit exceeded - will retry later",
    "AUTH_FAILED": "Instagram authentication failed - check credentials",
    "MEDIA_ERROR": "Media file could not be processed",
    "NETWORK_ERROR": "Network connection failed",
    "TIMEOUT": "Request timed out - Instagram may be slow",
    "INVALID_MEDIA": "Media format not supported by Instagram",
    "PERMISSION_DENIED": "Permission denied - check account permissions",
    "ACCOUNT_ISSUE": "Issue with Instagram account - manual check required",
    "UNKNOWN": "An unexpected error occurred",
}


def get_error_type(exception: Exception) -> str:
    """Determine error type from exception.

    Args:
        exception: The caught exception

    Returns:
        Error type string
    """
    error_str = str(exception).lower()
    exc_type = type(exception).__name__.lower()

    # Check for specific error patterns
    if "rate" in error_str or "limit" in error_str or "429" in error_str:
        return "RATE_LIMIT"
    if "auth" in error_str or "401" in error_str or "403" in error_str:
        return "AUTH_FAILED"
    if "timeout" in error_str or "timed out" in error_str:
        return "TIMEOUT"
    if "network" in error_str or "connection" in error_str:
        return "NETWORK_ERROR"
    if "media" in error_str or "image" in error_str or "video" in error_str:
        return "MEDIA_ERROR"
    if "permission" in error_str:
        return "PERMISSION_DENIED"
    if "account" in error_str:
        return "ACCOUNT_ISSUE"
    if "api" in error_str or "instagram" in exc_type:
        return "API_ERROR"

    return "UNKNOWN"


def get_user_friendly_error(error_type: str, raw_error: str = "") -> str:
    """Convert error type to user-friendly message.

    Story 4-7, Task 8.2: Map common errors to user-friendly messages.

    Args:
        error_type: Error category
        raw_error: Original error message for context

    Returns:
        User-friendly error description
    """
    base_message = ERROR_TYPE_MESSAGES.get(
        error_type,
        ERROR_TYPE_MESSAGES["UNKNOWN"],
    )

    # Add specific details for certain errors
    raw_lower = raw_error.lower()

    if error_type == "MEDIA_ERROR":
        if "size" in raw_lower:
            return f"{base_message}: Image may be too large"
        if "format" in raw_lower:
            return f"{base_message}: Unsupported file format"
        if "resolution" in raw_lower:
            return f"{base_message}: Image resolution not supported"

    if error_type == "RATE_LIMIT":
        # Don't expose internal retry details
        return base_message

    if error_type == "AUTH_FAILED":
        return f"{base_message} - check token expiration"

    if error_type == "TIMEOUT":
        return f"{base_message} - will retry automatically"

    return base_message


def format_error_for_notification(
    error_type: str,
    raw_error: str,
) -> tuple[str, str]:
    """Format error for Discord notification.

    Story 4-7, Task 8.5: Format embed with appropriate content.

    Args:
        error_type: Error category
        raw_error: Original error message

    Returns:
        Tuple of (user_friendly_message, error_type_display)
    """
    user_message = get_user_friendly_error(error_type, raw_error)
    type_display = error_type.replace("_", " ").title()

    return user_message, type_display


__all__ = [
    "ERROR_TYPE_MESSAGES",
    "get_error_type",
    "get_user_friendly_error",
    "format_error_for_notification",
]
