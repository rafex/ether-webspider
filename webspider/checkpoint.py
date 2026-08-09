"""webspider.checkpoint — Mission state persistence and resume.

Checkpoints are stored as JSON files under ``checkpoints/<mission_id>/``:
    state.json   — mission definition, visited URLs, frontier, findings, step count.
    memory.jsonl — serialized agent memory steps (one JSON object per line).

Usage:
    from webspider.checkpoint import (
        save_checkpoint, load_checkpoint, create_step_callback,
        create_state_tools,
    )

    # As a utility
    state = load_checkpoint("my_mission")
    callback = create_step_callback("my_mission", agent.memory.steps)

    # State tools for the agent
    tools = create_state_tools(mission_id, state_ref)
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast


def _checkpoints_base() -> str:
    return os.environ.get("WEBSPIDER_CHECKPOINTS", "checkpoints")


def _mission_dir(mission_id: str) -> str:
    return os.path.join(_checkpoints_base(), mission_id)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_checkpoint(mission_id: str, state: dict) -> str:
    """Persist mission state to disk.

    Args:
        mission_id: Unique identifier for this mission.
        state: Dict with keys: mission, step, visited, frontier, findings.

    Returns:
        Path to the saved state file.
    """
    d = _mission_dir(mission_id)
    _ensure_dir(d)

    state["last_step_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["mission_id"] = mission_id

    state_path = os.path.join(d, "state.json")
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    return state_path


def load_checkpoint(mission_id: str) -> dict | None:
    """Load mission state from disk.

    Args:
        mission_id: Unique identifier for the mission.

    Returns:
        State dict or None if the checkpoint does not exist.
    """
    state_path = os.path.join(_mission_dir(mission_id), "state.json")
    if not os.path.isfile(state_path):
        return None

    with open(state_path, encoding="utf-8") as f:
        return cast(dict, json.load(f))


def save_memory(mission_id: str, memory_steps: list) -> str:
    """Serialize agent memory steps to JSONL.

    Uses step.dict() (smolagents MemoryStep API) and falls back to repr.

    Args:
        mission_id: Unique identifier for this mission.
        memory_steps: List of smolagents memory step objects (with .dict()).

    Returns:
        Path to the saved memory file.
    """
    d = _mission_dir(mission_id)
    _ensure_dir(d)

    memory_path = os.path.join(d, "memory.jsonl")
    with open(memory_path, "w", encoding="utf-8") as f:
        for step in memory_steps:
            try:
                if hasattr(step, "dict"):
                    step_dict = step.dict()
                elif isinstance(step, dict):
                    step_dict = step
                else:
                    step_dict = {"step_type": type(step).__name__, "repr": repr(step)}
                f.write(json.dumps(step_dict, ensure_ascii=False, default=str) + "\n")
            except Exception:
                f.write(json.dumps({"error": "serialization_failed", "step_type": type(step).__name__}) + "\n")

    return memory_path


def load_memory(mission_id: str) -> list[dict]:
    """Load serialized memory steps from JSONL.

    Args:
        mission_id: Unique identifier for the mission.

    Returns:
        List of step dicts.
    """
    memory_path = os.path.join(_mission_dir(mission_id), "memory.jsonl")
    if not os.path.isfile(memory_path):
        return []

    steps = []
    with open(memory_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    steps.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return steps


def create_step_callback(mission_id: str) -> Callable:
    """Create a step callback that persists memory after each agent step.

    smolagents calls step callbacks as ``callback(memory_step, agent=self)``
    (see agents.py:_finalize_step). We use the ``agent`` kwarg to access
    ``agent.memory.steps`` directly.

    Args:
        mission_id: Unique identifier for the mission.

    Returns:
        A callable suitable for use as a step callback.
    """

    def _on_step(memory_step: Any = None, agent: Any = None) -> None:
        if agent is not None and hasattr(agent, "memory") and agent.memory.steps:
            save_memory(mission_id, agent.memory.steps)

    return _on_step


# ── State tools for the agent ──────────────────────────────────────────────────


def create_state_tools(mission_id: str, state_ref: dict) -> dict[str, Callable]:
    """Create the full set of state management tools for the agent.

    Tools mutate the shared ``state_ref`` dict so the agent can track
    visited URLs, the frontier, and findings across steps.

    Args:
        mission_id: Unique identifier for the mission.
        state_ref: Mutable dict (mission, step, visited, frontier, findings).

    Returns:
        Dict of tool_name → callable.
    """
    return {
        "add_finding": _create_add_finding(state_ref),
        "mark_visited": _create_mark_visited(state_ref),
        "add_to_frontier": _create_add_to_frontier(state_ref),
        "state_summary": _create_state_summary(state_ref),
        "save_checkpoint": _create_save_checkpoint(mission_id, state_ref),
        "load_checkpoint": _create_load_checkpoint(mission_id, state_ref),
    }


def _create_add_finding(state_ref: dict) -> Callable:
    def _add_finding(url: str, finding_type: str = "unknown", confidence: float = 0.5, notes: str = "") -> str:
        """Register a discovered finding."""
        for f in state_ref.get("findings", []):
            if f.get("url") == url:
                f.update(type=finding_type, confidence=confidence, notes=notes)
                return f"Updated finding: {url} [{finding_type}]"

        state_ref.setdefault("findings", []).append(
            {"url": url, "type": finding_type, "confidence": confidence, "notes": notes}
        )
        return f"Finding added: {url} [{finding_type}]"

    return _add_finding


def _create_mark_visited(state_ref: dict) -> Callable:
    def _mark_visited(url: str) -> str:
        """Mark a URL as visited (no-op if already visited)."""
        visited = state_ref.setdefault("visited", [])
        if url not in visited:
            visited.append(url)
            return f"Marked visited: {url}"
        return f"Already visited: {url}"

    return _mark_visited


def _create_add_to_frontier(state_ref: dict) -> Callable:
    def _add_to_frontier(url: str, priority: float = 0.5, reason: str = "") -> str:
        """Add a URL to the exploration frontier with a priority score."""
        frontier = state_ref.setdefault("frontier", [])
        for item in frontier:
            if item.get("url") == url:
                item["priority"] = max(item.get("priority", 0), priority)
                item["reason"] = reason or item.get("reason", "")
                return f"Updated frontier priority for {url}"

        frontier.append({"url": url, "priority": priority, "reason": reason})
        return f"Added to frontier: {url} (priority {priority:.2f})"

    return _add_to_frontier


def _create_state_summary(state_ref: dict) -> Callable:
    def _state_summary() -> str:
        """Return a compact JSON summary of current exploration state."""
        summary = {
            "step": state_ref.get("step", 0),
            "visited_count": len(state_ref.get("visited", [])),
            "frontier_count": len(state_ref.get("frontier", [])),
            "findings_count": len(state_ref.get("findings", [])),
            "top_findings": state_ref.get("findings", [])[-5:],
            "top_frontier": sorted(state_ref.get("frontier", []), key=lambda x: x.get("priority", 0), reverse=True)[:5],
        }
        return json.dumps(summary, ensure_ascii=False, indent=2)

    return _state_summary


def _create_save_checkpoint(mission_id: str, state_ref: dict) -> Callable:
    def _save_checkpoint(reason: str = "") -> str:
        """Save current mission state to checkpoint."""
        state_ref["checkpoint_reason"] = reason
        path = save_checkpoint(mission_id, dict(state_ref))
        return f"Checkpoint saved to {path}"

    return _save_checkpoint


def _create_load_checkpoint(mission_id: str, state_ref: dict) -> Callable:
    def _load_checkpoint() -> str:
        """Load mission state from the last checkpoint."""
        loaded = load_checkpoint(mission_id)
        if loaded is None:
            return "No checkpoint found."

        _excluded = ("mission_id", "last_step_at", "checkpoint_reason")
        for key, value in loaded.items():
            if key not in _excluded:
                state_ref[key] = value
        return (
            f"Checkpoint loaded: step {loaded.get('step', 0)}, "
            f"{len(loaded.get('visited', []))} visited, "
            f"{len(loaded.get('findings', []))} findings."
        )

    return _load_checkpoint
