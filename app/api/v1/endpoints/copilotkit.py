"""
CopilotKit integration endpoint (optional).
This is CORE INFRASTRUCTURE - Do not modify.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
import structlog

from langchain_core.messages import HumanMessage

from app.core.dependencies import UserContextDep
from app.core.config import settings
from app.agents.graph_builder import agent_graph
from app.agents.state import AgentState
from app.services import copilotkit_service

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
            # Handle chat action through agent (non-streaming).
            # Multi-turn memory is handled by LangGraph checkpointer via thread_id.
            params = request.parameters or {}
            message_text = params.get("message", "")

            initial_state: AgentState = {
                "messages": [HumanMessage(content=message_text)],
                "thread_id": request.thread_id or f"thread_{user.user_id}",
                "user_id": user.user_id,
                "user_email": user.email,
                "user_role": user.role,
                "current_step": "plan",
                "iteration_count": 0,
                "max_iterations": 3,
                "tool_results": None,
                "widget_type": None,
                "widget_data": None,
            }

            config = {"configurable": {"thread_id": initial_state["thread_id"]}}

            agent_result = await agent_graph.ainvoke(initial_state, config)

            formatted = copilotkit_service.format_response(
                agent_result,
                include_widget=True,
            )

            return CopilotKitResponse(
                result=formatted,
                widget=formatted.get("widget"),
            )

        # Default action handling via generic formatter
        raw_result: Any = None

        if request.action == "query":
            # Handle direct query action (placeholder)
            raw_result = {"message": "Query action handler not implemented"}

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown action: {request.action}",
            )

        formatted_action = copilotkit_service.format_action_response(
            action=request.action,
            result=raw_result,
            success=True,
        )
        return CopilotKitResponse(
            result=formatted_action,
            widget=None,
        )

    except Exception as e:
        logger.error("CopilotKit action failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Action failed: {str(e)}",
        )


@router.post("/stream")
async def copilotkit_stream(
    request: CopilotKitRequest,
    user: UserContextDep,
):
    """CopilotKit streaming endpoint using agent graph.

    Streams agent execution as CopilotKit-compatible SSE events.
    """

    if not settings.COPILOTKIT_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="CopilotKit integration is disabled",
        )

    if not settings.ENABLE_STREAMING:
        raise HTTPException(
            status_code=503,
            detail="Streaming is disabled",
        )

    async def event_generator():
        try:
            params = request.parameters or {}
            message_text = params.get("message", "")

            thread_id = request.thread_id or f"thread_{user.user_id}"

            messages_history = await _build_message_history(
                thread_id=thread_id,
                user=user,
                latest_user_message=message_text,
            )

            initial_state: AgentState = {
                "messages": messages_history,
                "thread_id": thread_id,
                "user_id": user.user_id,
                "user_email": user.email,
                "user_role": user.role,
                "current_step": "plan",
                "iteration_count": 0,
                "max_iterations": 3,
                "tool_results": None,
                "widget_type": None,
                "widget_data": None,
            }

            config = {"configurable": {"thread_id": initial_state["thread_id"]}}

            agent_stream = agent_graph.astream(initial_state, config)

            async for sse_chunk in copilotkit_service.format_stream(agent_stream):
                yield sse_chunk

        except Exception as e:
            logger.error("CopilotKit streaming failed", error=str(e))
            error_event = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
