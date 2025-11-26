from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

# Async tool callable: (arguments, user_context) -> result
ToolCallable = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]]


@dataclass
class ToolMeta:
    """
    Metadata describing a tool for the LLM planner and for documentation.
    """
    name: str
    description: str
    arguments_schema: Optional[Dict[str, Any]] = None  # Optional, JSON-schema-like
    examples: Optional[str] = None  # Optional, short usage examples


# Global registries
TOOLS: Dict[str, ToolCallable] = {}
TOOL_META: Dict[str, ToolMeta] = {}


def register_tool(
    name: str,
    func: ToolCallable,
    description: str,
    arguments_schema: Optional[Dict[str, Any]] = None,
    examples: Optional[str] = None,
) -> None:
    """
    Register a tool in the global registry.

    Args:
        name: Unique tool name used by the planner and in prompts.
        func: Async callable accepting (arguments, user_context) and returning a dict.
        description: What this tool does and when to use it.
        arguments_schema: Optional description of expected arguments (types, required fields).
        examples: Optional example of user requests that should trigger this tool.

    Raises:
        ValueError: If a tool with the same name is already registered.
    """
    if name in TOOLS:
        raise ValueError(f"Tool '{name}' is already registered")

    TOOLS[name] = func
    TOOL_META[name] = ToolMeta(
        name=name,
        description=description,
        arguments_schema=arguments_schema,
        examples=examples,
    )


def get_available_tools_description() -> str:
    """
    Return a human-readable description of available tools for planner prompts.

    The description includes:
    - Tool name
    - Human description
    - Brief arguments schema (if provided)
    - Example usage (if provided)
    """
    if not TOOL_META:
        return "No tools are currently available."

    lines = []
    # Sort by name for deterministic ordering
    for name in sorted(TOOL_META.keys()):
        meta = TOOL_META[name]
        lines.append(f"- {meta.name}: {meta.description}")
        if meta.arguments_schema:
            lines.append(f"  Expected arguments: {meta.arguments_schema}")
        if meta.examples:
            lines.append(f"  Example: {meta.examples}")
    return "\n".join(lines)