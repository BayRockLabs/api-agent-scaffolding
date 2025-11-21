"""
FastAPI dependency injection for core services.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from fastapi import Request, Depends
from typing import Annotated

from app.core.auth import UserContext, validate_user_context
from app.core.config import settings
from app.core.exceptions import AuthenticationException


def get_user_context(request: Request) -> UserContext:
    """
    Extract and validate user context from request headers.

    This dependency is automatically injected by auth_middleware.
    If middleware is bypassed (shouldn't happen), we extract from headers.

    Args:
        request: FastAPI request object

    Returns:
        UserContext: Validated user context

    Raises:
        AuthenticationException: If user context is invalid
    """
    # First try to get from request state (set by middleware)
    if hasattr(request.state, "user"):
        return request.state.user

    # Fallback: extract from headers
    user_id = request.headers.get(settings.AUTH_USERID_HEADER)
    email = request.headers.get(settings.AUTH_EMAIL_HEADER)
    role = request.headers.get(settings.AUTH_ROLE_HEADER)

    try:
        return validate_user_context(user_id, email, role)
    except ValueError as e:
        raise AuthenticationException(str(e))


# Type alias for dependency injection
UserContextDep = Annotated[UserContext, Depends(get_user_context)]
