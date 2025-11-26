"""
Core agent nodes for LangGraph.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, Any, List
import structlog

from app.agents.state import AgentState
from app.services import llm_service

logger = structlog.get_logger()


def planning_node(state: AgentState) -> Dict[str, Any]:
    """
    Planning node - analyze request and create execution plan.
    Developers can customize planning logic in domain services.
    """
    logger.info("Agent: Planning", user_id=state["user_id"])

    # Basic planning logic (developers extend in services)
    last_message = state["messages"][-1].content if state["messages"] else ""

    return {
        "current_step": "query",
        "iteration_count": state.get("iteration_count", 0) + 1,
    }


async def query_execution_node(state: AgentState) -> Dict[str, Any]:
    """
    Query execution node - execute tools based on plan.
    Tool selection happens here.
    """
    logger.info("Agent: Query execution", user_id=state["user_id"])

    # Prepare messages for LLM provider
    llm_messages: List[Dict[str, str]] = []
    for msg in state.get("messages", []):
        if isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        else:
            role = getattr(msg, "type", "assistant")

        llm_messages.append({
            "role": role,
            "content": getattr(msg, "content", ""),
        })

    # Call LLM service (non-streaming) to get assistant response
    response = await llm_service.chat_completion(messages=llm_messages)

    # Extract assistant content from provider response
    assistant_content = ""
    try:
        choices = response.get("choices", [])
        if choices:
            message = choices[0].get("message") or {}
            assistant_content = message.get("content", "") or message.get("text", "")
    except Exception:
        assistant_content = ""

    if assistant_content:
        state_messages = list(state.get("messages", []))
        state_messages.append(AIMessage(content=assistant_content))
        return {
            "messages": state_messages,
            "current_step": "validate",
        }

    return {
        "current_step": "validate",
    }


def validation_node(state: AgentState) -> Dict[str, Any]:
    """
    Validation node - check if results are sufficient.
    """
    logger.info("Agent: Validating results", user_id=state["user_id"])

    return {
        "current_step": "end",  # Or "refine" if needs improvement
    }


def refinement_node(state: AgentState) -> Dict[str, Any]:
    """
    Refinement node - improve query based on validation.
    """
    logger.info("Agent: Refining query", user_id=state["user_id"])

    return {
        "current_step": "plan",  # Loop back to planning
    }


def should_refine(state: AgentState) -> str:
    """
    Decision function: should we refine or end?
    """
    # Check iteration limit
    if state.get("iteration_count", 0) >= state.get("max_iterations", 3):
        return "end"

    # Check if results are good (developers customize this logic)
    if state.get("tool_results"):
        return "end"

    return "refine"
