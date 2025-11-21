"""
Main API router - aggregates all endpoint routers.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    health,
    agent,
    stream,
    copilotkit,
    files,
)

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router)
api_router.include_router(agent.router)
api_router.include_router(stream.router)
api_router.include_router(copilotkit.router)
api_router.include_router(files.router)

# DEVELOPER: Add your custom endpoint routers here
# Example:
# from app.api.v1.endpoints import kpis
# api_router.include_router(kpis.router)
