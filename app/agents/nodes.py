"""
Core agent nodes for LangGraph.
This is CORE INFRASTRUCTURE - Do not modify.
"""

from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, Any, List
import json
import structlog

from app.agents.state import AgentState
from app.services import llm_service
from prompts.tool_planner import (
    TOOL_PLANNER_SYSTEM_PROMPT,
    TOOL_ANSWER_SYSTEM_PROMPT,
)
from app.tools import TOOLS, get_available_tools_description

logger = structlog.get_logger()


def _extract_text_from_llm_response(response: Dict[str, Any]) -> str:
    """
    Helper to extract the primary text content from a chat completion response.
    """
    try:
        choices = response.get("choices", [])
        if choices:
            message = choices[0].get("message") or {}
            return (
                message.get("content", "")
                or message.get("text", "")
                or ""
            )
    except Exception:
        return ""
    return ""


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

    messages = state.get("messages", []) or []

    # Find latest user message content
    last_user_text = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_text = getattr(msg, "content", "")
            break

    # ------------------------------------------------------------------
    # 1) Planner call: decide which tool (if any) to use
    # ------------------------------------------------------------------
    available_tools_desc = get_available_tools_description()
    planner_system_prompt = TOOL_PLANNER_SYSTEM_PROMPT.format(
        available_tools=available_tools_desc
    )

    planner_messages: List[Dict[str, str]] = [
        {"role": "system", "content": planner_system_prompt},
        {"role": "user", "content": last_user_text},
    ]

    planner_response = await llm_service.chat_completion(messages=planner_messages)
    plan_text = _extract_text_from_llm_response(planner_response).strip()

    plan: Dict[str, Any] = {}
    try:
        plan = json.loads(plan_text) if plan_text else {}
    except json.JSONDecodeError:
        logger.warning(
            "agent.tool_planner_invalid_json",
            raw_response=plan_text,
        )
        plan = {
            "tool": "none",
            "reason": "Planner returned invalid JSON",
            "arguments": {},
        }

    tool_name = (plan.get("tool") or "none").strip()
    tool_arguments: Dict[str, Any] = plan.get("arguments") or {}
    tool_results: List[Dict[str, Any]] = list(state.get("tool_results") or [])

    # ------------------------------------------------------------------
    # 2) Execute selected tool (if any) via registry
    # ------------------------------------------------------------------
    if tool_name != "none":
        tool_fn = TOOLS.get(tool_name)
        if tool_fn is None:
            logger.warning(
                "agent.tool_not_registered",
                tool=tool_name,
            )
        else:
            user_context = {
                "user_id": state["user_id"],
                "user_email": state["user_email"],
                "user_role": state.get("user_role"),
            }
            try:
                logger.info(
                    "agent.tool_execution_start",
                    tool=tool_name,
                    user_id=state["user_id"],
                )
                tool_result = await tool_fn(tool_arguments, user_context)
                logger.info(
                    "agent.tool_execution_success",
                    tool=tool_name,
                    user_id=state["user_id"],
                )
                tool_results.append(
                    {
                        "tool": tool_name,
                        "arguments": tool_arguments,
                        "result": tool_result,
                    }
                )
            except Exception as exc:
                logger.error(
                    "agent.tool_execution_failed",
                    tool=tool_name,
                    user_id=state["user_id"],
                    error=str(exc),
                )
                tool_results.append(
                    {
                        "tool": tool_name,
                        "arguments": tool_arguments,
                        "error": str(exc),
                    }
                )

    # ------------------------------------------------------------------
    # 3) Final answer call: LLM uses messages + tool_results
    # ------------------------------------------------------------------
    answer_system_prompt = TOOL_ANSWER_SYSTEM_PROMPT

    # Construct context snippet for tool results (if any)
    tool_context_text = ""
    if tool_results:
        try:
            tool_context_text = "Tool results:\n" + json.dumps(
                tool_results, default=str
            )[:4000]
        except Exception:
            tool_context_text = "Tool results are available but could not be serialized."

    answer_messages: List[Dict[str, str]] = []
    answer_messages.append({"role": "system", "content": answer_system_prompt})

    # Include conversation history as seen by the provider
    for msg in messages:
        if isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        else:
            role = getattr(msg, "type", "assistant")

        answer_messages.append(
            {
                "role": role,
                "content": getattr(msg, "content", ""),
            }
        )

    if tool_context_text:
        # Tool context provided as an additional system message
        answer_messages.append(
            {
                "role": "system",
                "content": tool_context_text,
            }
        )

    answer_response = await llm_service.chat_completion(messages=answer_messages)
    assistant_content = _extract_text_from_llm_response(answer_response)

    if assistant_content:
        state_messages = list(messages)
        state_messages.append(AIMessage(content=assistant_content))
        return {
            "messages": state_messages,
            "tool_results": tool_results,
            "current_step": "validate",
        }

    return {
        "tool_results": tool_results,
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