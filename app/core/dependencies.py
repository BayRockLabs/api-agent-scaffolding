"""
FastAPI dependency injection for core services.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from fastapi import Request, Depends, Header
from typing import Annotated, Optional

from app.core.auth import UserContext, validate_user_context
from app.core.config import settings
from app.core.exceptions import AuthenticationException


def get_user_context(
    request: Request,
    user_id: Optional[str] = Header(
        None,
        alias=settings.AUTH_USERID_HEADER,
        description="User identifier for RBAC (header)",
    ),
    email: Optional[str] = Header(
        None,
        alias=settings.AUTH_EMAIL_HEADER,
        description="User email for RBAC (header)",
    ),
    role: Optional[str] = Header(
        None,
        alias=settings.AUTH_ROLE_HEADER,
        description="User role for RBAC (header)",
    ),
) -> UserContext:
    """Extract and validate user context from request headers.

    This dependency is normally set by auth_middleware via request.state.user.
    If middleware is bypassed, headers are used. In local environment,
    a default user context is used when headers are missing.
    """

    # Prefer value set by auth middleware (if present)
    if hasattr(request.state, "user"):
        return request.state.user

    # Local development convenience: allow missing headers and fall back
    # to a default user so interactive docs work without manual headers.
    if settings.ENVIRONMENT == "local" and not user_id and not email:
        return UserContext(
            user_id="local-user",
            email="local@example.com",
            role="developer",
        )

    try:
        return validate_user_context(user_id, email, role)
    except ValueError as e:
        raise AuthenticationException(str(e))


# Type alias for dependency injection
UserContextDep = Annotated[UserContext, Depends(get_user_context)]
