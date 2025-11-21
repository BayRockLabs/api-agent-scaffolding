"""
LangGraph cyclic graph builder.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from langgraph.graph import StateGraph, END
import structlog

from app.agents.state import AgentState
from app.agents.nodes import (
    planning_node,
    query_execution_node,
    validation_node,
    refinement_node,
    should_refine,
)
from app.core.checkpointer import checkpointer

logger = structlog.get_logger()


def build_agent_graph():
    """
    Build LangGraph cyclic graph: Plan  Query  Validate  Refine (loop)
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("plan", planning_node)
    graph.add_node("query", query_execution_node)
    graph.add_node("validate", validation_node)
    graph.add_node("refine", refinement_node)

    # Define flow
    graph.set_entry_point("plan")
    graph.add_edge("plan", "query")
    graph.add_edge("query", "validate")

    # Conditional routing: validate  refine OR end
    graph.add_conditional_edges(
        "validate",
        should_refine,
        {
            "refine": "refine",
            "end": END,
        },
    )

    # Refinement loops back to planning
    graph.add_edge("refine", "plan")

    # Compile with checkpointer
    logger.info("Compiling agent graph with checkpointing")
    return graph.compile(checkpointer=checkpointer)


# Global compiled graph
agent_graph = build_agent_graph()
