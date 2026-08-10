"""webspider.agent — Core agent: builds a CodeAgent, runs a mission, handles resume.

Usage:
    from webspider.agent import run_mission, resume_mission

    result = run_mission(mission, mcp_tools, model)
"""

from __future__ import annotations

import os
import time
from typing import Any

from webspider.capabilities import get_capabilities_tools
from webspider.checkpoint import (
    create_state_tools,
    create_step_callback,
    load_checkpoint,
    load_memory,
    redact_sensitive_data,
    save_checkpoint,
)
from webspider.config import get_model
from webspider.mission import build_prompt, build_resume_prompt
from webspider.tool_adapter import STATE_TOOL_SCHEMAS, as_agent_tool

_ENDPOINT_CAPABILITIES = {
    "capture_browser_network",
    "extract_api_artifacts",
    "inspect_http_endpoint",
    "replay_request",
    "browser_session",
    "inspect_grpc_endpoint",
}


def _validate_mission(mission: dict[str, Any]) -> None:
    """Enforce execution safety before creating an agent or contacting MCP."""
    mode = mission.get("discovery_mode", mission.get("mode", "passive"))
    if mode not in {"passive", "probe", "active"}:
        raise ValueError("discovery_mode must be passive, probe, or active")
    if mode == "active" and (not mission.get("allowed_domains") or not mission.get("active_confirmed")):
        raise ValueError("active discovery requires allowed_domains and active_confirmed=true")
    browser = mission.get("browser", {})
    session = mission.get("session", {})
    if browser.get("attach") and not browser.get("session_id") and not session.get("attach_endpoint"):
        raise ValueError("attach requires browser.session_id or session.attach_endpoint")
    if int(mission.get("max_steps", 30)) < 1 or int(mission.get("max_requests", 200)) < 1:
        raise ValueError("max_steps and max_requests must be positive")


def _require_mcp_capabilities(mcp_tools: list) -> None:
    names = {getattr(tool, "name", "") for tool in mcp_tools}
    missing = sorted(_ENDPOINT_CAPABILITIES - names)
    if missing:
        raise RuntimeError(f"ether-websearch MCP is missing required capabilities: {', '.join(missing)}")


def _result_from_state(
    mission_id: str, mission: dict[str, Any], state_ref: dict, *, ok: bool, result: str = "", error: str = ""
) -> dict:
    """Build a consistent structured mission result."""
    output = {
        "ok": ok,
        "mission_id": mission_id,
        "goal": mission.get("goal", ""),
        "result": result,
        "findings": redact_sensitive_data(state_ref.get("findings", [])),
        "requests": redact_sensitive_data(state_ref.get("requests", [])),
        "artifacts": redact_sensitive_data(state_ref.get("artifacts", [])),
        "steps": state_ref.get("step", 0),
        "requests_used": state_ref.get("requests_used", 0),
        "visited_count": len(state_ref.get("visited", [])),
        "checkpoint_dir": os.path.join("checkpoints", mission_id),
    }
    if error:
        output["error"] = error
    return output


def _build_state_ref(mission: dict) -> dict:
    """Create the mutable state dict that the agent and checkpoint tools share."""
    return {
        "mission": mission,
        "step": 0,
        "visited": [],
        "frontier": [],
        "findings": [],
        "requests": [],
        "artifacts": [],
        "requests_used": 0,
        "tool_calls": 0,
        "coverage": {},
    }


def _get_agent_tools(mcp_tools: list, mission_id: str, state_ref: dict, on_finding: Any = None) -> dict:
    """Assemble all tools for the agent.

    Returns a dict of name -> tool callable.
    """
    tools: dict[str, Any] = {}

    def _persist_state() -> None:
        save_checkpoint(mission_id, state_ref)

    # MCP tools from ether-websearch
    for tool in mcp_tools:
        name = getattr(tool, "name", None)
        if name:

            def _call_mcp(bound_tool: Any = tool, **kwargs: Any) -> Any:
                return bound_tool(**kwargs)

            inputs = getattr(tool, "inputs", {}) or {}
            description = str(getattr(tool, "description", name))
            tools[name] = as_agent_tool(
                name,
                _call_mcp,
                inputs,
                description,
                after_call=_persist_state,
            )

    # State management tools (mutate shared state_ref)
    state_tools = create_state_tools(mission_id, state_ref, on_finding=on_finding)
    for name, function in state_tools.items():
        inputs, description = STATE_TOOL_SCHEMAS[name]
        tools[name] = as_agent_tool(
            name,
            function,
            inputs,
            description,
            after_call=_persist_state,
        )

    # Capability tools
    tool_names = sorted(name for name in tools if name not in {"request_capability"})
    for cap_tool in get_capabilities_tools(tool_names):
        name = getattr(cap_tool, "__name__", None)
        if name:
            inputs, description = STATE_TOOL_SCHEMAS.get(name, ({}, name))
            tools[name] = as_agent_tool(
                name,
                cap_tool,
                inputs,
                description,
                after_call=_persist_state,
            )

    return tools


def _generate_mission_id(goal: str) -> str:
    """Generate a short mission ID from the goal and timestamp."""
    import hashlib

    ts = int(time.time())
    goal_hash = hashlib.md5(goal.encode()).hexdigest()[:8]
    return f"m{ts}_{goal_hash}"


def run_mission(
    mission: dict,
    mcp_tools: list | None = None,
    model: Any = None,
    mission_id: str | None = None,
    on_finding: Any = None,
    credentials: dict[str, str] | None = None,
) -> dict:
    """Run a spider mission from scratch.

    Args:
        mission: Mission dict from mission_from_args or mission_from_file.
        mcp_tools: List of MCP tools (from get_mcp_tools()). If None,
                   tools won't be loaded (useful for dry-run/testing).
        model: Pre-configured LLM model. If None, creates from config.
        mission_id: Custom mission ID. Auto-generated if None.
        on_finding: Optional callback called with each new finding.

    Returns:
        Result dict with outcomes, findings, steps, checkpoint path.
    """
    from smolagents import CodeAgent

    if mission_id is None:
        mission_id = _generate_mission_id(mission["goal"])

    _validate_mission(mission)

    if model is None:
        model = get_model()

    state_ref = _build_state_ref(mission)
    state_ref["runtime_credentials"] = dict(credentials or {})

    tools_dict: dict = {}
    if mcp_tools is not None:
        _require_mcp_capabilities(mcp_tools)
    tools_dict = _get_agent_tools(mcp_tools or [], mission_id, state_ref, on_finding=on_finding)

    prompt = build_prompt(mission)

    step_callback = create_step_callback(mission_id, state_ref)

    agent = CodeAgent(
        tools=list(tools_dict.values()),
        model=model,
        max_steps=mission["max_steps"],
        verbosity_level=2,
        step_callbacks=[step_callback],
    )

    try:
        result = agent.run(prompt)

        save_checkpoint(mission_id, state_ref)

        return {
            "ok": True,
            "mission_id": mission_id,
            "goal": mission["goal"],
            "result": str(result) if result else "",
            "findings": redact_sensitive_data(state_ref.get("findings", [])),
            "requests": redact_sensitive_data(state_ref.get("requests", [])),
            "artifacts": redact_sensitive_data(state_ref.get("artifacts", [])),
            "steps": state_ref.get("step", 0),
            "requests_used": state_ref.get("requests_used", 0),
            "visited_count": len(state_ref.get("visited", [])),
            "checkpoint_dir": os.path.join("checkpoints", mission_id),
        }
    except Exception as e:
        save_checkpoint(mission_id, state_ref)
        return {
            "ok": False,
            "mission_id": mission_id,
            "goal": mission["goal"],
            "error": str(e),
            "findings": redact_sensitive_data(state_ref.get("findings", [])),
            "requests": redact_sensitive_data(state_ref.get("requests", [])),
            "artifacts": redact_sensitive_data(state_ref.get("artifacts", [])),
            "steps": state_ref.get("step", 0),
            "requests_used": state_ref.get("requests_used", 0),
            "visited_count": len(state_ref.get("visited", [])),
            "checkpoint_dir": os.path.join("checkpoints", mission_id),
        }


def resume_mission(
    mission_id: str,
    mcp_tools: list | None = None,
    model: Any = None,
    credentials: dict[str, str] | None = None,
) -> dict:
    """Resume a mission from a checkpoint.

    Args:
        mission_id: ID of the mission to resume.
        mcp_tools: List of MCP tools (from get_mcp_tools()).
        model: Pre-configured LLM model. If None, creates from config.

    Returns:
        Result dict with outcomes, findings, steps, checkpoint path.

    Raises:
        ValueError: If the checkpoint does not exist.
    """
    from smolagents import CodeAgent

    state = load_checkpoint(mission_id)
    if state is None:
        raise ValueError(
            f"No checkpoint found for mission {mission_id!r}. Check {os.path.join('checkpoints', mission_id)}"
        )

    if model is None:
        model = get_model()

    mission = state.get("mission", {})
    if not mission:
        raise ValueError(f"Checkpoint {mission_id!r} has no mission definition.")

    _validate_mission(mission)
    state_ref = dict(state)
    state_ref["runtime_credentials"] = dict(credentials or {})
    for key, default in (
        ("requests", []),
        ("artifacts", []),
        ("requests_used", 0),
        ("tool_calls", 0),
        ("coverage", {}),
    ):
        state_ref.setdefault(key, default)

    if state_ref.get("step", 0) >= mission.get("max_steps", 30):
        return _result_from_state(mission_id, mission, state_ref, ok=True, result="Mission already reached max_steps.")

    tools_dict: dict = {}
    if mcp_tools is not None:
        _require_mcp_capabilities(mcp_tools)
    tools_dict = _get_agent_tools(mcp_tools or [], mission_id, state_ref)

    prompt = build_resume_prompt(mission, state)
    memory_steps = load_memory(mission_id)
    remaining_steps = max(1, mission.get("max_steps", 30) - state.get("step", 0))

    step_callback = create_step_callback(mission_id, state_ref)

    agent = CodeAgent(
        tools=list(tools_dict.values()),
        model=model,
        max_steps=remaining_steps,
        verbosity_level=2,
        step_callbacks=[step_callback],
    )

    # Rebuild memory from saved steps (best-effort)
    if memory_steps:
        _restore_memory(agent, memory_steps)

    try:
        result = agent.run(prompt, reset=len(memory_steps) == 0)

        save_checkpoint(mission_id, state_ref)

        return {
            "ok": True,
            "mission_id": mission_id,
            "goal": mission.get("goal", ""),
            "result": str(result) if result else "",
            "findings": redact_sensitive_data(state_ref.get("findings", [])),
            "requests": redact_sensitive_data(state_ref.get("requests", [])),
            "artifacts": redact_sensitive_data(state_ref.get("artifacts", [])),
            "steps": state_ref.get("step", 0),
            "requests_used": state_ref.get("requests_used", 0),
            "visited_count": len(state_ref.get("visited", [])),
            "checkpoint_dir": os.path.join("checkpoints", mission_id),
        }
    except Exception as e:
        save_checkpoint(mission_id, state_ref)
        return {
            "ok": False,
            "mission_id": mission_id,
            "goal": mission.get("goal", ""),
            "error": str(e),
            "findings": state_ref.get("findings", []),
            "requests": state_ref.get("requests", []),
            "artifacts": state_ref.get("artifacts", []),
            "steps": state_ref.get("step", 0),
            "requests_used": state_ref.get("requests_used", 0),
            "visited_count": len(state_ref.get("visited", [])),
            "checkpoint_dir": os.path.join("checkpoints", mission_id),
        }


def _restore_memory(agent: Any, memory_steps: list[dict]) -> None:
    """Best-effort restore of agent memory from saved step dicts.

    Reconstructs smolagents memory objects from serialized dicts.
    Failures are silently skipped; state tools provide the durable data.
    """
    from smolagents import AgentMemory
    from smolagents.memory import ActionStep, TaskStep

    system_prompt = getattr(agent.memory, "system_prompt", None)
    if system_prompt is not None:
        system_prompt = system_prompt.system_prompt
    # Default from CodeAgent
    original_steps = list(agent.memory.steps) if agent.memory.steps else []

    try:
        agent.memory = AgentMemory(system_prompt=system_prompt or "")
    except Exception:
        return

    for step_dict in memory_steps:
        if isinstance(step_dict, dict) and step_dict.get("error") == "serialization_failed":
            continue

        try:
            if "task" in step_dict and "step_number" not in step_dict:
                agent.memory.steps.append(TaskStep(task=str(step_dict.get("task", ""))))
            elif isinstance(step_dict, dict):
                agent.memory.steps.append(
                    ActionStep(
                        step_number=step_dict.get("step_number", 0),
                        observations=step_dict.get("observations", ""),
                        code_action=step_dict.get("code_action"),
                        model_output=step_dict.get("model_output"),
                        action_output=step_dict.get("action_output"),
                        error=None,
                    )
                )
        except Exception:
            continue

    # Ensure at least the original system prompt step is present
    if not agent.memory.steps and original_steps:
        agent.memory.steps = original_steps
