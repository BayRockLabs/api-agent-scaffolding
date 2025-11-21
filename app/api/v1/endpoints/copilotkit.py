"""
CopilotKit integration endpoint (optional).
This is CORE INFRASTRUCTURE - Do not modify.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import structlog

from app.core.dependencies import UserContextDep
from app.core.config import settings
from app.agents.graph_builder import agent_graph
from app.widgets.factory import widget_factory

logger = structlog.get_logger()
router = APIRouter(prefix="/copilotkit", tags=["CopilotKit"])


class CopilotKitRequest(BaseModel):
    """CopilotKit request format"""

    action: str
    parameters: Optional[Dict[str, Any]] = None
    thread_id: Optional[str] = None


class CopilotKitResponse(BaseModel):
    """CopilotKit response format"""

    result: Any
    widget: Optional[Dict[str, Any]] = None


@router.post("/action", response_model=CopilotKitResponse)
async def copilotkit_action(
    request: CopilotKitRequest,
    user: UserContextDep,
):
    """
    CopilotKit action endpoint.

    Executes agent actions and returns structured responses
    for Generative UI rendering.
    """

    if not settings.COPILOTKIT_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="CopilotKit integration is disabled",
        )

    try:
        logger.info(
            "CopilotKit action",
            action=request.action,
            user_id=user.user_id,
        )

        # Route to appropriate handler based on action
        # Developers can extend with custom actions

        if request.action == "chat":
            # Handle chat action through agent
            # (Implementation similar to agent endpoint)
            pass

        elif request.action == "query":
            # Handle direct query action
            pass

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown action: {request.action}",
            )

        # Return formatted response
        return CopilotKitResponse(
            result="Action completed",
            widget=None,
        )

    except Exception as e:
        logger.error("CopilotKit action failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Action failed: {str(e)}",
        )
