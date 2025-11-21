"""
LangSmith tracing middleware.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class TracingMiddleware(BaseHTTPMiddleware):
    """Integrate LangSmith tracing with requests"""

    async def dispatch(self, request: Request, call_next):
        """Add tracing context to request"""

        # Add tracing metadata to request state
        if settings.LANGCHAIN_TRACING_V2:
            request.state.tracing_enabled = True

            # Add trace metadata
            request.state.trace_metadata = {
                "path": request.url.path,
                "method": request.method,
                "correlation_id": getattr(request.state, "correlation_id", None),
            }

            # Add user info if available
            if hasattr(request.state, "user"):
                request.state.trace_metadata.update(
                    {
                        "user_id": request.state.user.user_id,
                        "user_role": request.state.user.role,
                    }
                )

        return await call_next(request)
