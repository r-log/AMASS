"""
Service result type for consistent return values across services.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ServiceResult:
    """
    Standardized result for service methods that return success/failure with optional data.

    Attributes:
        success: Whether the operation succeeded
        data: Optional result data (e.g. model instance, dict)
        message: Success or error message
    """

    success: bool
    message: str
    data: Optional[Any] = None

    @classmethod
    def ok(cls, data: Any = None, message: str = "Success") -> "ServiceResult":
        """Create a successful result."""
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str, data: Any = None) -> "ServiceResult":
        """Create a failed result."""
        return cls(success=False, message=message, data=data)

    def as_tuple(self) -> tuple:
        """Return as (success, data, message) for backward compatibility."""
        return (self.success, self.data, self.message)
