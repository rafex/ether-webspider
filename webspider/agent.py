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

    # State management tools (mutate shared state_ref)
    tools.update(create_state_tools(mission_id, state_ref))

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

    tools_dict: dict = {}
    if mcp_tools is not None:
        tools_dict = _get_agent_tools(mcp_tools, mission_id, state_ref)

    prompt = build_prompt(mission)

    step_callback = create_step_callback(mission_id)

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

    state_ref = dict(state)

    tools_dict: dict = {}
    if mcp_tools is not None:
        tools_dict = _get_agent_tools(mcp_tools, mission_id, state_ref)

    prompt = build_resume_prompt(mission, state)
    memory_steps = load_memory(mission_id)
    remaining_steps = max(1, mission.get("max_steps", 30) - state.get("step", 0))

    step_callback = create_step_callback(mission_id)

    agent = CodeAgent(
        tools=tools_dict,
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
