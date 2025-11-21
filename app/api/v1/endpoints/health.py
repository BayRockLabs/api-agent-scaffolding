"""
Health check endpoints.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from fastapi import APIRouter, status
from datetime import datetime
import structlog

from app.models.responses import HealthResponse
from app.core.config import settings
from app.infrastructure.snowflake.engine import snowflake_engine

logger = structlog.get_logger()
router = APIRouter(tags=["Health"])


@router.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint"""
    return HealthResponse(
        status="running",
        version=settings.APP_VERSION,
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint - tests all critical services.
    Returns 200 if healthy, 503 if any service is down.
    """
    services = {}
    overall_status = "healthy"

    # Test Snowflake connection
    try:
        if snowflake_engine.test_connection():
            services["snowflake"] = "healthy"
        else:
            services["snowflake"] = "unhealthy"
            overall_status = "degraded"
    except Exception as e:
        logger.error("Snowflake health check failed", error=str(e))
        services["snowflake"] = "unhealthy"
        overall_status = "degraded"

    # Test S3 connection
    try:
        from app.infrastructure.storage.s3_client import s3_client

        if s3_client.client:
            services["s3"] = "healthy"
        else:
            services["s3"] = "unhealthy"
            overall_status = "degraded"
    except Exception as e:
        logger.error("S3 health check failed", error=str(e))
        services["s3"] = "unhealthy"
        overall_status = "degraded"

    # Test Checkpointer
    try:
        from app.core.checkpointer import checkpointer

        if checkpointer:
            services["checkpointer"] = "healthy"
        else:
            services["checkpointer"] = "unhealthy"
            overall_status = "degraded"
    except Exception as e:
        logger.error("Checkpointer health check failed", error=str(e))
        services["checkpointer"] = "unhealthy"
        overall_status = "degraded"

    status_code = (
        status.HTTP_200_OK
        if overall_status == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return HealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        services=services,
    )


@router.get("/health/ready")
async def readiness_probe():
    """Kubernetes readiness probe"""
    return {"status": "ready"}


@router.get("/health/live")
async def liveness_probe():
    """Kubernetes liveness probe"""
    return {"status": "alive"}
