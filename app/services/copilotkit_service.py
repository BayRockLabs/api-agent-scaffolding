"""
CopilotKit integration service for Generative UI.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from typing import Dict, Any, AsyncIterator, List, Optional
import json
import structlog

from app.core.config import settings
from app.widgets.factory import widget_factory

logger = structlog.get_logger()


class CopilotKitService:
    """
    Service for formatting agent responses for CopilotKit Generative UI.
    
    Converts agent outputs into CopilotKit-compatible formats:
    - Structured actions
    - UI widgets
    - Streaming events
    """
    
    def __init__(self):
        self.enabled = settings.COPILOTKIT_ENABLED
        self.streaming = settings.COPILOTKIT_STREAMING
    
    def format_response(
        self,
        agent_result: Dict[str, Any],
        include_widget: bool = True,
    ) -> Dict[str, Any]:
        """
        Format agent response for CopilotKit.
        
        Args:
            agent_result: Agent execution result with messages and widget data
            include_widget: Whether to include widget in response
            
        Returns:
            CopilotKit-formatted response
        """
        if not self.enabled:
            logger.warning("CopilotKit is disabled")
            return agent_result
        
        # Extract message content
        messages = agent_result.get("messages", [])
        last_message = messages[-1] if messages else None
        content = last_message.content if last_message else ""
        
        response = {
            "type": "response",
            "content": content,
            "role": "assistant",
        }
        
        # Add widget if available
        if include_widget and agent_result.get("widget_type"):
            widget = self._construct_widget(
                widget_type=agent_result["widget_type"],
                widget_data=agent_result.get("widget_data", {}),
            )
            
            if widget:
                response["widget"] = widget
        
        # Add metadata
        response["metadata"] = {
            "conversation_id": agent_result.get("thread_id"),
            "iteration_count": agent_result.get("iteration_count", 0),
            "current_step": agent_result.get("current_step"),
        }
        
        logger.info(
            "CopilotKit response formatted",
            has_widget=("widget" in response),
            content_length=len(content),
        )
        
        return response
    
    async def format_stream(
        self,
        agent_stream: AsyncIterator[Dict[str, Any]],
    ) -> AsyncIterator[str]:
        """
        Format agent stream for CopilotKit SSE.
        
        Args:
            agent_stream: Async iterator of agent events
            
        Yields:
            SSE-formatted event strings
        """
        if not self.enabled or not self.streaming:
            logger.warning("CopilotKit streaming is disabled")
            return
        
        try:
            async for event in agent_stream:
                # Format each event type for CopilotKit
                for node_name, node_state in event.items():
                    # Send progress event
                    progress_event = {
                        "type": "progress",
                        "node": node_name,
                        "step": node_state.get("current_step"),
                    }
                    yield self._format_sse_event(progress_event)
                    
                    # Send message chunks if available
                    if "messages" in node_state:
                        last_message = node_state["messages"][-1]
                        if hasattr(last_message, 'content'):
                            message_event = {
                                "type": "message",
                                "content": last_message.content,
                                "role": "assistant",
                            }
                            yield self._format_sse_event(message_event)
                    
                    # Send widget if available
                    if node_state.get("widget_type"):
                        widget = self._construct_widget(
                            widget_type=node_state["widget_type"],
                            widget_data=node_state.get("widget_data", {}),
                        )
                        
                        if widget:
                            widget_event = {
                                "type": "widget",
                                "widget": widget,
                            }
                            yield self._format_sse_event(widget_event)
            
            # Send completion event
            done_event = {"type": "done"}
            yield self._format_sse_event(done_event)
            
        except Exception as e:
            logger.error("CopilotKit streaming error", error=str(e))
            error_event = {
                "type": "error",
                "error": str(e),
            }
            yield self._format_sse_event(error_event)
    
    def _construct_widget(
        self,
        widget_type: str,
        widget_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Construct a CopilotKit-compatible widget.
        
        Args:
            widget_type: Type of widget (table, chart, map, etc.)
            widget_data: Widget data
            
        Returns:
            Widget dict or None
        """
        try:
            if widget_type == "table":
                return widget_factory.create_table(
                    title=widget_data.get("title", "Data Table"),
                    columns=widget_data.get("columns", []),
                    rows=widget_data.get("rows", []),
                    metadata=widget_data.get("metadata"),
                )
            
            elif widget_type == "chart":
                return widget_factory.create_chart(
                    chart_type=widget_data.get("chart_type", "bar"),
                    title=widget_data.get("title", "Chart"),
                    data=widget_data.get("data", {}),
                    options=widget_data.get("options"),
                )
            
            elif widget_type == "map":
                return widget_factory.create_map(
                    title=widget_data.get("title", "Map"),
                    markers=widget_data.get("markers", []),
                    center=widget_data.get("center", {"lat": 0, "lng": 0}),
                    zoom=widget_data.get("zoom", 10),
                )
            
            elif widget_type == "card":
                return widget_factory.create_card(
                    title=widget_data.get("title", ""),
                    content=widget_data.get("content", ""),
                    subtitle=widget_data.get("subtitle"),
                    metadata=widget_data.get("metadata"),
                )
            
            elif widget_type == "list":
                return widget_factory.create_list(
                    title=widget_data.get("title", "List"),
                    items=widget_data.get("items", []),
                    metadata=widget_data.get("metadata"),
                )
            
            else:
                logger.warning(f"Unknown widget type: {widget_type}")
                return None
                
        except Exception as e:
            logger.error(
                "Widget construction failed",
                widget_type=widget_type,
                error=str(e),
            )
            return None
    
    def _format_sse_event(self, event: Dict[str, Any]) -> str:
        """
        Format event as Server-Sent Event string.
        
        Args:
            event: Event dictionary
            
        Returns:
            SSE-formatted string
        """
        return f"data: {json.dumps(event)}\n\n"
    
    def format_action_response(
        self,
        action: str,
        result: Any,
        success: bool = True,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Format response for CopilotKit action execution.
        
        Args:
            action: Action name
            result: Action result
            success: Whether action succeeded
            error: Error message if failed
            
        Returns:
            CopilotKit action response
        """
        response = {
            "action": action,
            "success": success,
        }
        
        if success:
            response["result"] = result
        else:
            response["error"] = error or "Action failed"
        
        return response
    
    def create_action_metadata(
        self,
        action_name: str,
        description: str,
        parameters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Create CopilotKit action metadata for client registration.
        
        Args:
            action_name: Action identifier
            description: Human-readable description
            parameters: List of parameter definitions
            
        Returns:
            Action metadata dict
        """
        return {
            "name": action_name,
            "description": description,
            "parameters": parameters,
            "handler": "server",  # Indicates server-side execution
        }


# Global instance
copilotkit_service = CopilotKitService()
