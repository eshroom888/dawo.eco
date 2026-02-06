"""Custom exceptions for Research Pool module.

Provides specific exception types for error handling in the
research pool operations. All exceptions inherit from ResearchPoolError.

Exceptions:
    - ResearchPoolError: Base exception for all research pool errors
    - ItemNotFoundError: Raised when a research item is not found
    - ValidationError: Raised when input validation fails
    - DatabaseError: Raised when a database operation fails
"""

from typing import Optional
from uuid import UUID


class ResearchPoolError(Exception):
    """Base exception for Research Pool operations.

    All research pool specific exceptions inherit from this class.
    Allows catching all research pool errors with a single except clause.
    """

    def __init__(self, message: str, details: Optional[dict] = None):
        """Initialize with error message and optional details.

        Args:
            message: Human-readable error description
            details: Optional dictionary with additional context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ItemNotFoundError(ResearchPoolError):
    """Raised when a research item cannot be found.

    Typically raised by repository operations when querying by ID
    and the item does not exist in the database.
    """

    def __init__(self, item_id: UUID):
        """Initialize with the missing item ID.

        Args:
            item_id: UUID of the item that was not found
        """
        super().__init__(
            message=f"Research item not found: {item_id}",
            details={"item_id": str(item_id)},
        )
        self.item_id = item_id


class ValidationError(ResearchPoolError):
    """Raised when input validation fails.

    Used when schema validation passes but business rules fail.
    """

    def __init__(self, field: str, message: str):
        """Initialize with field name and validation message.

        Args:
            field: Name of the field that failed validation
            message: Description of the validation failure
        """
        super().__init__(
            message=f"Validation failed for '{field}': {message}",
            details={"field": field},
        )
        self.field = field


class DatabaseError(ResearchPoolError):
    """Raised when a database operation fails.

    Wraps SQLAlchemy and database driver exceptions with
    context about the operation that failed.

    Note: Error details are sanitized to avoid leaking internal
    database information in production error responses.
    """

    # Error types that are safe to expose (common, non-sensitive)
    SAFE_ERROR_TYPES = frozenset({
        "IntegrityError",
        "OperationalError",
        "TimeoutError",
        "ConnectionError",
    })

    def __init__(self, operation: str, original_error: Exception):
        """Initialize with operation context and original error.

        Args:
            operation: Description of the operation that failed
            original_error: The underlying database exception
        """
        error_type = type(original_error).__name__

        # Only expose error type if it's in the safe list
        safe_error_type = error_type if error_type in self.SAFE_ERROR_TYPES else "DatabaseError"

        super().__init__(
            message=f"Database operation failed: {operation}",
            details={"operation": operation, "error_type": safe_error_type},
        )
        self.operation = operation
        # Store original error for internal logging, but don't expose in details
        self._original_error = original_error

    @property
    def original_error(self) -> Exception:
        """Access the original error for internal debugging."""
        return self._original_error
