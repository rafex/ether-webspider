"""webspider.agent — Core agent: builds a CodeAgent, runs a mission, handles resume.

Usage:
    from webspider.agent import run_mission, resume_mission

    result = run_mission(mission, state_ref, mcp_tools_context)
"""

from __future__ import annotations

import os
import time
from typing import Any

from webspider.capabilities import get_capabilities_tools
from webspider.checkpoint import (
    create_load_checkpoint_tool,
    create_save_checkpoint_tool,
    create_step_callback,
    load_checkpoint,
    load_memory,
    save_checkpoint,
)
from webspider.config import get_model
from webspider.mission import build_prompt, build_resume_prompt


def _build_state_ref(mission: dict) -> dict:
    """Create the mutable state dict that the agent and checkpoint tools share."""
    return {
        "mission": mission,
        "step": 0,
        "visited": [],
        "frontier": [],
        "findings": [],
    }


def _get_agent_tools(mcp_tools: list, mission_id: str, state_ref: dict) -> dict:
    """Assemble all tools for the agent.

    Returns a dict of name -> tool callable.
    """
    tools: dict[str, Any] = {}

    # MCP tools from ether-websearch
    for tool in mcp_tools:
        name = getattr(tool, "name", None)
        if name:
            tools[name] = tool

    # Local tools
    tools["save_checkpoint"] = create_save_checkpoint_tool(mission_id, state_ref)
    tools["load_checkpoint"] = create_load_checkpoint_tool(mission_id, state_ref)

    # Capability tools
    for cap_tool in get_capabilities_tools():
        name = getattr(cap_tool, "__name__", None)
        if name:
            tools[name] = cap_tool

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

    if model is None:
        model = get_model()

    state_ref = _build_state_ref(mission)

    tools_dict = {}
    if mcp_tools is not None:
        tools_dict = _get_agent_tools(mcp_tools, mission_id, state_ref)

    step_callback = create_step_callback(mission_id)
    prompt = build_prompt(mission)

    agent = CodeAgent(
        tools=tools_dict,
        model=model,
        max_steps=mission["max_steps"],
        verbosity_level=2,
        step_callbacks=[step_callback],
    )

    try:
        result = agent.run(prompt)

        save_checkpoint(mission_id, dict(state_ref))

        return {
            "ok": True,
            "mission_id": mission_id,
            "goal": mission["goal"],
            "result": str(result) if result else "",
            "findings": state_ref.get("findings", []),
            "visited_count": len(state_ref.get("visited", [])),
            "checkpoint_dir": os.path.join("checkpoints", mission_id),
        }
    except Exception as e:
        save_checkpoint(mission_id, dict(state_ref))
        return {
            "ok": False,
            "mission_id": mission_id,
            "goal": mission["goal"],
            "error": str(e),
            "findings": state_ref.get("findings", []),
            "visited_count": len(state_ref.get("visited", [])),
            "checkpoint_dir": os.path.join("checkpoints", mission_id),
        }


def resume_mission(
    mission_id: str,
    mcp_tools: list | None = None,
    model: Any = None,
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
    from smolagents import AgentMemory, CodeAgent

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

    state_ref = dict(state)

    tools_dict = {}
    if mcp_tools is not None:
        tools_dict = _get_agent_tools(mcp_tools, mission_id, state_ref)

    step_callback = create_step_callback(mission_id)
    prompt = build_resume_prompt(mission, state)

    memory_steps = load_memory(mission_id)

    agent = CodeAgent(
        tools=tools_dict,
        model=model,
        max_steps=mission.get("max_steps", 30) - state.get("step", 0),
        verbosity_level=2,
        step_callbacks=[step_callback],
    )

    if memory_steps:
        agent.memory = AgentMemory()
        for step_dict in memory_steps:
            try:
                from smolagents import ActionStep

                step = ActionStep.from_dict(step_dict)
                agent.memory.steps.append(step)
            except Exception:
                pass

    try:
        result = agent.run(prompt, reset=False)

        save_checkpoint(mission_id, dict(state_ref))

        return {
            "ok": True,
            "mission_id": mission_id,
            "goal": mission.get("goal", ""),
            "result": str(result) if result else "",
            "findings": state_ref.get("findings", []),
            "visited_count": len(state_ref.get("visited", [])),
            "checkpoint_dir": os.path.join("checkpoints", mission_id),
        }
    except Exception as e:
        save_checkpoint(mission_id, dict(state_ref))
        return {
            "ok": False,
            "mission_id": mission_id,
            "goal": mission.get("goal", ""),
            "error": str(e),
            "findings": state_ref.get("findings", []),
            "visited_count": len(state_ref.get("visited", [])),
            "checkpoint_dir": os.path.join("checkpoints", mission_id),
        }
