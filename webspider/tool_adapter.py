"""Adapt closure-based state helpers to smolagents Tool instances."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def as_agent_tool(
    name: str,
    function: Callable[..., Any],
    inputs: dict[str, dict[str, Any]],
    description: str,
    after_call: Callable[[], None] | None = None,
) -> Any:
    """Build a Tool without relying on inspect.getsource for closures."""
    from smolagents import Tool

    class DynamicTool(Tool):
        def __init__(self) -> None:
            self.is_initialized = True

    # The adapter deliberately forwards arbitrary keyword arguments so it can
    # run both closure-based state helpers and remote MCP tools. The schema is
    # authoritative; smolagents' source-signature check is not applicable.
    DynamicTool.skip_forward_signature_validation = True
    DynamicTool.name = name
    DynamicTool.description = description
    DynamicTool.inputs = inputs
    DynamicTool.output_type = "string"

    def forward(**kwargs: Any) -> Any:
        try:
            return function(**kwargs)
        finally:
            if after_call is not None:
                after_call()

    DynamicTool.forward = staticmethod(forward)
    return DynamicTool()


STATE_TOOL_SCHEMAS: dict[str, tuple[dict[str, dict[str, Any]], str]] = {
    "add_finding": (
        {
            "url": {"type": "string", "description": "Finding URL"},
            "finding_type": {"type": "string", "description": "Finding type", "nullable": True},
            "confidence": {"type": "number", "description": "Confidence from 0 to 1", "nullable": True},
            "notes": {"type": "string", "description": "Notes", "nullable": True},
        },
        "Record a legacy URL finding.",
    ),
    "record_endpoint_finding": (
        {"finding": {"type": "object", "description": "Structured endpoint finding"}},
        "Record a structured endpoint finding.",
    ),
    "record_request": (
        {"request": {"type": "object", "description": "Captured request"}},
        "Record and deduplicate a captured request.",
    ),
    "record_artifact": (
        {"artifact": {"type": "object", "description": "API artifact"}},
        "Record API contract evidence.",
    ),
    "mark_visited": (
        {"url": {"type": "string", "description": "Visited URL"}},
        "Mark a URL as visited.",
    ),
    "add_to_frontier": (
        {
            "url": {"type": "string", "description": "URL to explore"},
            "priority": {"type": "number", "description": "Priority from 0 to 1", "nullable": True},
            "reason": {"type": "string", "description": "Why it is relevant", "nullable": True},
        },
        "Add a URL to the exploration frontier.",
    ),
    "state_summary": ({}, "Return current mission state summary."),
    "save_checkpoint": (
        {"reason": {"type": "string", "description": "Checkpoint reason", "nullable": True}},
        "Persist redacted mission state.",
    ),
    "load_checkpoint": ({}, "Restore redacted mission state."),
    "get_user_instruction": ({}, "Read the next user instruction."),
    "get_session_credentials": ({}, "Read explicitly supplied runtime credentials for authorized login."),
    "fetch_capabilities": ({}, "Return capabilities registered for this agent."),
    "request_capability": (
        {
            "name": {"type": "string", "description": "Capability name"},
            "description": {"type": "string", "description": "Requested capability"},
            "use_case": {"type": "string", "description": "Concrete use case"},
        },
        "Request a missing capability from ether-websearch.",
    ),
}
