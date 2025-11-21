"""
Main FastAPI application.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.core.config import settings
from app.core.exceptions import AppException
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.tracing_middleware import TracingMiddleware
from app.api.v1.router import api_router
from app.infrastructure.snowflake.engine import snowflake_engine

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""

    # Startup
    logger.info(
        "Starting Enterprise AI Agent Platform",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    # Test Snowflake connection
    try:
        snowflake_engine.test_connection()
        logger.info("Snowflake connection verified")
    except Exception as e:
        logger.error("Snowflake connection failed", error=str(e))

    # Test checkpointer
    try:
        from app.core.checkpointer import checkpointer

        logger.info("Checkpointer initialized", backend=settings.CHECKPOINT_BACKEND)
    except Exception as e:
        logger.error("Checkpointer initialization failed", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down Enterprise AI Agent Platform")
    snowflake_engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise AI Agent Platform with FastAPI, LangGraph, and Snowflake",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom Middleware (order matters!)
app.add_middleware(TracingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)


# Global Exception Handler
@app.exception_handler(AppException)
async def app_exception_handler(request, exc: AppException):
    """Handle application exceptions"""
    logger.error(
        "Application exception",
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


# Include API Router
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
    }
