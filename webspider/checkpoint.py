"""webspider.checkpoint — Mission state persistence and resume.

Checkpoints are stored as JSON files under ``checkpoints/<mission_id>/``:
    state.json   — mission definition, visited URLs, frontier, findings, step count.
    memory.jsonl — serialized agent memory steps (one JSON object per line).

Usage:
    from webspider.checkpoint import save_checkpoint, load_checkpoint, create_step_callback

    # As an agent tool
    result = save_checkpoint(state_json)

    # As a utility
    state = load_checkpoint("my_mission")
    callback = create_step_callback("my_mission")
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

_CHECKPOINTS_DIR = os.environ.get("WEBSPIDER_CHECKPOINTS", "checkpoints")


def _mission_dir(mission_id: str) -> str:
    return os.path.join(_CHECKPOINTS_DIR, mission_id)


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

    Args:
        mission_id: Unique identifier for this mission.
        memory_steps: List of smolagents memory step objects (with .to_dict()).

    Returns:
        Path to the saved memory file.
    """
    d = _mission_dir(mission_id)
    _ensure_dir(d)

    memory_path = os.path.join(d, "memory.jsonl")
    with open(memory_path, "w", encoding="utf-8") as f:
        for step in memory_steps:
            try:
                step_dict = step.to_dict() if hasattr(step, "to_dict") else step
                f.write(json.dumps(step_dict, ensure_ascii=False) + "\n")
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


def create_step_callback(mission_id: str, memory_steps: list | None = None) -> Callable:
    """Create a step callback that persists memory after each agent step.

    The returned callback can be passed to CodeAgent's step_callbacks parameter.

    Args:
        mission_id: Unique identifier for the mission.
        memory_steps: Reference to the agent's memory.steps list (mutable).

    Returns:
        A callable suitable for use as a step callback.
    """

    def _on_step(step_data: Any = None) -> None:
        if memory_steps is not None and memory_steps:
            save_memory(mission_id, memory_steps)

    return _on_step


# ── State tools for the agent ──────────────────────────────────────────────────


def create_save_checkpoint_tool(mission_id: str, state_ref: dict) -> Callable:
    """Create a save_checkpoint tool for the agent to call.

    The tool serializes the current state_ref dict to the checkpoint file.
    The agent should update state_ref before calling this.

    Args:
        mission_id: Unique identifier for the mission.
        state_ref: Mutable dict reference the agent populates with state.

    Returns:
        A callable tool function.
    """

    def _save_checkpoint(reason: str = "") -> str:
        """Save current mission state to checkpoint.

        Args:
            reason: Optional description of why the checkpoint is being saved.
        """
        state_ref["checkpoint_reason"] = reason
        path = save_checkpoint(mission_id, dict(state_ref))
        return f"Checkpoint saved to {path}"

    return _save_checkpoint


def create_load_checkpoint_tool(mission_id: str, state_ref: dict) -> Callable:
    """Create a load_checkpoint tool for the agent to call.

    Loads the checkpoint state into state_ref.

    Args:
        mission_id: Unique identifier for the mission.
        state_ref: Mutable dict reference to populate with loaded state.

    Returns:
        A callable tool function.
    """

    def _load_checkpoint() -> str:
        """Load mission state from the last checkpoint."""
        loaded = load_checkpoint(mission_id)
        if loaded is None:
            return "No checkpoint found."

        _excluded = ("mission_id", "last_step_at", "checkpoint_reason")
        for key, value in loaded.items():
            if key not in _excluded:
                state_ref[key] = value
        return f"Checkpoint loaded: step {loaded.get('step', 0)}, {len(loaded.get('visited', []))} URLs visited, {len(loaded.get('findings', []))} findings."

    return _load_checkpoint
