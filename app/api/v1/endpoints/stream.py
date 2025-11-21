"""
Server-Sent Events (SSE) streaming endpoint.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
import json
import asyncio
import structlog

from app.models.requests import ChatRequest
from app.core.dependencies import UserContextDep
from app.agents.graph_builder import agent_graph
from app.agents.state import AgentState
from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post("/stream")
async def agent_stream(
    request: ChatRequest,
    user: UserContextDep,
):
    """
    Streaming agent interaction using Server-Sent Events.

    - Real-time token streaming
    - Progress updates
    - Widget delivery
    """

    if not settings.ENABLE_STREAMING:
        return {"error": "Streaming is disabled"}

    async def event_generator():
        """Generate SSE events"""
        try:
            # Prepare initial state
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

            config = {
                "configurable": {"thread_id": initial_state["thread_id"]}
            }

            logger.info(
                "Streaming started",
                user_id=user.user_id,
                thread_id=initial_state["thread_id"],
            )

            # Stream agent execution
            async for event in agent_graph.astream(initial_state, config):
                # Send progress updates
                for node_name, node_state in event.items():
                    chunk = {
                        "type": "progress",
                        "node": node_name,
                        "step": node_state.get("current_step"),
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for client processing

            # Get final result
            final_state = await agent_graph.aget_state(config)

            # Send final message
            if final_state and final_state.values.get("messages"):
                last_message = final_state.values["messages"][-1]
                chunk = {
                    "type": "message",
                    "content": last_message.content,
                    "role": "assistant",
                }
                yield f"data: {json.dumps(chunk)}\n\n"

            # Send widget if available
            if final_state.values.get("widget_type"):
                widget = {
                    "type": "widget",
                    "widget_type": final_state.values["widget_type"],
                    "widget_data": final_state.values.get("widget_data"),
                }
                yield f"data: {json.dumps(widget)}\n\n"

            # Send completion
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

            logger.info("Streaming completed", user_id=user.user_id)

        except Exception as e:
            logger.error("Streaming failed", user_id=user.user_id, error=str(e))
            error_chunk = {
                "type": "error",
                "message": str(e),
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
