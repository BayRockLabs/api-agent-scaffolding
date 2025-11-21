"""
Base tool for agent tools.
DEVELOPER ZONE: Extend this for your custom tools.
"""

from langchain.tools import BaseTool as LangChainBaseTool
from pydantic import Field
from app.core.auth import UserContext


class BaseTool(LangChainBaseTool):
    """
    Base tool providing user context and common utilities.
    All agent tools should inherit from this.
    """

    user_context: UserContext = Field(..., description="User context for RBAC")

    # Developers implement _run() or _arun() in subclasses
