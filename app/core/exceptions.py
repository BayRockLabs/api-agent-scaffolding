"""
Core exception handling system.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from typing import Optional, Dict, Any


class AppException(Exception):
    """Base application exception"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationException(AppException):
    """Authentication failed"""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTH_ERROR",
            details=details,
        )


class AuthorizationException(AppException):
    """User not authorized"""

    def __init__(self, message: str = "Not authorized", details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
            details=details,
        )


class ValidationException(AppException):
    """Validation error"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class NotFoundException(AppException):
    """Resource not found"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details,
        )


class SnowflakeException(AppException):
    """Snowflake operation failed"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="SNOWFLAKE_ERROR",
            details=details,
        )


class StorageException(AppException):
    """Storage operation failed"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="STORAGE_ERROR",
            details=details,
        )


class LLMException(AppException):
    """LLM operation failed"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=502,
            error_code="LLM_ERROR",
            details=details,
        )


class ToolExecutionException(AppException):
    """Agent tool execution failed"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            status_code=500,
            error_code="TOOL_ERROR",
            details=details,
        )
