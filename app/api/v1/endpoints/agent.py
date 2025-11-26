"""
Agent chat endpoints (non-streaming).
DEVELOPER ZONE: Customize agent behavior in domain services.
"""

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage
import structlog

from app.models.requests import ChatRequest
from app.models.responses import ChatResponse
from app.core.dependencies import UserContextDep
from app.agents.graph_builder import agent_graph
from app.agents.state import AgentState
from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(
    request: ChatRequest,
    user: UserContextDep,
):
    """
    Non-streaming agent chat interaction.

    - Natural language input
    - LangGraph cyclic reasoning
    - Returns response with optional widget
    """
    try:
        # Prepare agent state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=request.message)],
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

        # Configure agent with thread_id for checkpointing
        config = {
            "configurable": {"thread_id": initial_state["thread_id"]}
        }

        logger.info(
            "Agent invocation started",
            user_id=user.user_id,
            thread_id=initial_state["thread_id"],
        )

        # Invoke agent
        result = await agent_graph.ainvoke(initial_state, config)

        # Extract response
        last_message = result["messages"][-1] if result.get("messages") else None
        response_text = (
            last_message.content if last_message else "No response generated"
        )

        # Construct widget if available
        widget = None
        if result.get("widget_type") and result.get("widget_data"):
            widget = {
                "type": result["widget_type"],
                "data": result["widget_data"],
            }

        logger.info(
            "Agent invocation completed",
            user_id=user.user_id,
            has_widget=widget is not None,
        )

        return ChatResponse(
            thread_id=initial_state["thread_id"],
            message=response_text,
            widget=widget,
            metadata=request.metadata,
        )

    except Exception as e:
        logger.error(
            "Agent invocation failed",
            user_id=user.user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500, detail=f"Agent processing failed: {str(e)}"
        )
