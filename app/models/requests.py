"""Request models"""

from pydantic import Field
from typing import Optional, Dict, Any
from app.models.base import BaseModel


class ChatRequest(BaseModel):
    """Agent chat request"""

    message: str = Field(..., description="User message")
    thread_id: Optional[str] = Field(None, description="Conversation thread ID")
    stream: bool = Field(False, description="Enable streaming")
    metadata: Optional[Dict[str, Any]] = None


class QueryRequest(BaseModel):
    """Snowflake query request"""

    query_id: str = Field(..., description="Query template ID")
    parameters: Dict[str, Any] = Field(default_factory=dict)
