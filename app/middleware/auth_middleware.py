"""
Authentication middleware - extracts user from headers.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.core.auth import validate_user_context
from app.core.exceptions import AuthenticationException

logger = structlog.get_logger()


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Extract and validate user context from request headers.
    Attaches UserContext to request.state.user for downstream use.
    """

    # Endpoints that don't require authentication
    SKIP_AUTH_PATHS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next):
        """Process request and inject user context"""

        # Skip auth for public endpoints
        if request.url.path in self.SKIP_AUTH_PATHS:
            return await call_next(request)

        try:
            # Extract headers
            user_id = request.headers.get(settings.AUTH_USERID_HEADER)
            email = request.headers.get(settings.AUTH_EMAIL_HEADER)
            role = request.headers.get(settings.AUTH_ROLE_HEADER)

            # Validate and create user context
            user_context = validate_user_context(user_id, email, role)

            # Attach to request state
            request.state.user = user_context

            # Log authentication
            logger.info(
                "Request authenticated",
                user_id=user_context.user_id,
                email=user_context.email,
                role=user_context.role,
                path=request.url.path,
                method=request.method,
            )

            # Process request
            response = await call_next(request)
            return response

        except ValueError as e:
            logger.warning(
                "Authentication failed",
                error=str(e),
                path=request.url.path,
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": "AUTH_ERROR",
                    "message": "Authentication failed",
                    "details": str(e),
                },
            )
        except Exception as e:
            logger.error(
                "Unexpected authentication error",
                error=str(e),
                path=request.url.path,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "INTERNAL_ERROR",
                    "message": "Authentication processing failed",
                },
            )
