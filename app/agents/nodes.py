"""
Core agent nodes for LangGraph.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, Any
import structlog

from app.agents.state import AgentState

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


def query_execution_node(state: AgentState) -> Dict[str, Any]:
    """
    Query execution node - execute tools based on plan.
    Tool selection happens here.
    """
    logger.info("Agent: Query execution", user_id=state["user_id"])

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
