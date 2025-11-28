"""
Agent state definition with role-based access.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from typing import TypedDict, List, Optional, Dict, Any
from typing_extensions import Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """
    Complete agent state with RBAC.
    Role is injected from request headers for data filtering.
    """

    # Conversation
    messages: Annotated[List[BaseMessage], add_messages]
    thread_id: str

    # User Context (injected from headers)
    user_id: str
    user_email: str
    user_role: Optional[str]  # Used for role-based filtering in tools

    # Agent Flow Control
    current_step: str  # plan, query, validate, refine, end
    iteration_count: int
    max_iterations: int

    # Tool Execution
    tool_results: Optional[List[Dict[str, Any]]]

    # Widget Construction
    widget_type: Optional[str]
    widget_data: Optional[Dict[str, Any]]
