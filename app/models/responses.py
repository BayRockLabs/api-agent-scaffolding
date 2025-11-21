"""Response models"""

from pydantic import Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.base import BaseModel


class ChatResponse(BaseModel):
    """Agent chat response"""

    thread_id: str
    message: str
    role: str = "assistant"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    widget: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Optional[Dict[str, str]] = None
