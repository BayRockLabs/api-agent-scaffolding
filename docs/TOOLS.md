# Agent Tools and LLM-Based Tool Selection

This document explains how to add new agent tools and how they are used by the
LLM-based planner/executor in the agent graph.

## Architecture Overview

The agent stack is structured as follows:

- **Endpoints**
  - `/agent/chat`, `/agent/stream` (FastAPI)
  - `/copilotkit/action` (chat) and `/copilotkit/stream`
- **Agent graph**
  - Defined in `app/agents/graph_builder.py`
  - Nodes implemented in `app/agents/nodes.py`
- **LLM client**
  - OAuth-based HTTP client in `app/services/llm_service.py`
- **Tool planner & answer prompts**
  - Centralized in `prompts/tool_planner.py`
- **Tool registry**
  - Defined in `app/tools/__init__.py`

All entry points invoke the same `agent_graph`, which flows through the
`query_execution_node`. That node is responsible for:

1. Asking the LLM which tool (if any) to call.
2. Executing the selected tool in Python.
3. Asking the LLM to generate the final answer using tool results.

## Tool Registry

The global tool registry is defined in `app/tools/__init__.py`:

```python
from typing import Any, Awaitable, Callable, Dict

ToolCallable = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[Dict[str, Any]]]


# Global tool registry.
# Key: tool name (string used by the planner)
# Value: async callable (args: dict, user_context: dict) -> dict result
TOOLS: Dict[str, ToolCallable] = {}


def register_tool(name: str, func: ToolCallable) -> None:
    """Register a tool in the global registry."""
    if name in TOOLS:
        raise ValueError(f"Tool '{name}' is already registered")
    TOOLS[name] = func


def get_available_tools_description() -> str:
    """Return a human-readable description of available tools for planner prompts."""
    if not TOOLS:
        return "No tools are currently available."

    lines = []
    for name in sorted(TOOLS.keys()):
        # Placeholder description; extend with real metadata as needed.
        lines.append(f"- {name}: No description provided.")
    return "\n".join(lines)
```

### Tool Function Contract

Each tool must be an **async callable** with the following signature:

```python
async def my_tool(args: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
    ...
```

- `args`: A JSON-serializable dictionary of arguments chosen by the planner.
- `user_context`: A dictionary containing user information derived from
  `AgentState` (e.g. `user_id`, `user_email`, `user_role`).
- Return value: A JSON-serializable dictionary representing the tool result.

## Adding a New Tool

1. **Implement the tool function**

Create a new module under `app/tools/`, for example
`app/tools/sales_report_tool.py`:

```python
# app/tools/sales_report_tool.py
from typing import Dict, Any


async def sales_report_tool(args: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
    """Example tool that would generate a sales report.

    Args:
        args: Tool arguments (e.g. {"region": "EMEA", "year": 2024}).
        user_context: Current user context (user_id, user_email, user_role).

    Returns:
        A JSON-serializable dict with the tool result.
    """
    region = args.get("region", "ALL")
    year = args.get("year")

    # TODO: Implement real data access logic here (e.g. Snowflake query).
    # This placeholder just returns the inputs.
    return {
        "tool": "sales_report_tool",
        "region": region,
        "year": year,
        "data": [],
        "summary": f"Sales report for region={region}, year={year}",
    }
```

2. **Register the tool**

Register the tool in an appropriate initialization location, for example in
`app/tools/__init__.py`:

```python
from app.tools.sales_report_tool import sales_report_tool

register_tool("sales_report_tool", sales_report_tool)
```

> Note: If you prefer, you can register tools from a dedicated
> `app/tools/registry.py` module that is imported at startup.

3. **Describe the tool for the planner**

Update `get_available_tools_description()` (or the tool planner prompt) to
include a meaningful description, for example:

```python
def get_available_tools_description() -> str:
    if not TOOLS:
        return "No tools are currently available."

    lines = [
        "- sales_report_tool: Generate sales reports by region and year.",
        # Add more tools here as needed.
    ]
    return "\n".join(lines)
```

This helps the LLM understand when to select each tool.

## LLM-Based Tool Planning and Execution

The main orchestration happens in `app/agents/nodes.py` inside
`query_execution_node`.

### Planner Step

1. Extract the latest user message from `AgentState["messages"]`.
2. Build a system prompt using `TOOL_PLANNER_SYSTEM_PROMPT` from
   `prompts/tool_planner.py`, formatting in `available_tools` using
   `get_available_tools_description()`.
3. Call the LLM via `llm_service.chat_completion` to obtain a JSON plan:

```json
{
  "tool": "sales_report_tool" | "none",
  "reason": "...",
  "arguments": { ... }
}
```

### Tool Execution

If the planner selects a tool (`tool != "none"`):

- Look up `tool_fn = TOOLS[tool_name]`.
- Build `user_context` from `AgentState`.
- Execute `tool_result = await tool_fn(tool_arguments, user_context)`.
- Append to `tool_results` in state:

```python
tool_results.append({
    "tool": tool_name,
    "arguments": tool_arguments,
    "result": tool_result,
})
```

### Final Answer Step

After tool execution, `query_execution_node` calls the LLM again with
`TOOL_ANSWER_SYSTEM_PROMPT`:

- Includes the full conversation history as `user` / `assistant` messages.
- Includes a serialized summary of `tool_results` as an additional `system`
  message.
- The LLM produces the final assistant answer, which is appended as an
  `AIMessage` to `AgentState["messages"]`.

The node returns a partial state update containing:

- Updated `messages` (including the final answer).
- Updated `tool_results`.
- `current_step = "validate"`.

## How Endpoints Use Tools

Because all endpoints call the same `agent_graph`, they all benefit from
LLM-based tool selection and execution:

- `/agent/chat` and `/agent/stream` use `agent_graph.ainvoke` and
  `agent_graph.astream`.
- `/copilotkit/action` (with `action == "chat"`) calls `agent_graph.ainvoke`
  and then formats the result via `copilotkit_service.format_response()`.
- `/copilotkit/stream` uses `agent_graph.astream` wrapped by
  `copilotkit_service.format_stream()`.

As long as you register tools in the global `TOOLS` registry and describe them
in the planner prompt, the agent can intelligently select and execute them for
any of these entry points.

## Best Practices

- Keep tools **small, single-responsibility**, and focused on one domain task.
- Validate planner input (`arguments`) before executing a tool.
- Log tool invocations and failures for observability.
- Ensure tool results are **JSON-serializable** (e.g. convert datetimes to
  strings).
- Update `get_available_tools_description()` whenever you add or remove tools
  so the planner always has an up-to-date view.
